import cv2
import mediapipe as mp
import serial
import time
import tkinter as tk
from tkinter import ttk, messagebox
import serial.tools.list_ports # Pustaka untuk mendeteksi port serial

# --- Global Variables ---
arduino = None # Akan diisi setelah port dipilih
cap = None     # Objek kamera, akan diinisialisasi setelah port dikonfirmasi
is_running = False # Flag untuk mengontrol loop video

# --- MediaPipe & Servo Configuration (unchanged from previous version) ---
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
mp_draw = mp.solutions.drawing_utils
prev_hand_state = None # 'open' atau 'closed'

def get_hand_state(hand_landmarks):
    fingers_open = 0
    thumb_threshold_x = 0.05

    # Jari telunjuk (8 vs 7)
    if hand_landmarks.landmark[8].y < hand_landmarks.landmark[7].y:
        fingers_open += 1
    # Jari tengah (12 vs 11)
    if hand_landmarks.landmark[12].y < hand_landmarks.landmark[11].y:
        fingers_open += 1
    # Jari manis (16 vs 15)
    if hand_landmarks.landmark[16].y < hand_landmarks.landmark[15].y:
        fingers_open += 1
    # Jari kelingking (20 vs 19)
    if hand_landmarks.landmark[20].y < hand_landmarks.landmark[19].y:
        fingers_open += 1

    # Jempol (4 vs 3)
    if hand_landmarks.landmark[4].x < hand_landmarks.landmark[3].x - thumb_threshold_x or \
       hand_landmarks.landmark[4].x > hand_landmarks.landmark[3].x + thumb_threshold_x:
        fingers_open += 1

    if fingers_open >= 4:
        return 'open'
    else:
        return 'closed'

# --- Main Application Logic (runs after port is selected) ---
def start_hand_pose_detection(selected_port):
    global arduino, cap, is_running, prev_hand_state

    # 1. Initialize Arduino Serial Connection
    try:
        arduino = serial.Serial(selected_port, 9600, timeout=1)
        print(f"Koneksi serial ke Arduino berhasil di port {selected_port}!")
        time.sleep(2) # Give Arduino time to reset
    except serial.SerialException:
        messagebox.showerror("Error Serial", f"Gagal terhubung ke Arduino di {selected_port}. Pastikan port benar dan Arduino terhubung.")
        arduino = None
        return # Stop if serial connection fails

    # 2. Initialize Camera
    cap = cv2.VideoCapture(0) # You can add a selection for camera ID later if needed
    if not cap.isOpened():
        messagebox.showerror("Error Kamera", "Gagal membuka kamera. Pastikan kamera terhubung dan tidak digunakan aplikasi lain.")
        # Close Arduino connection if camera fails
        if arduino:
            arduino.close()
        return # Stop if camera fails

    # 3. Create OpenCV Window and Start Loop
    is_running = True
    prev_hand_state = None # Reset state for new run

    print("Program Python dimulai. Tekan 'q' untuk keluar.")

    while is_running and cap.isOpened():
        success, image = cap.read()
        if not success:
            print("Gagal membaca frame dari kamera.")
            break

        image = cv2.flip(image, 1)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = hands.process(image_rgb)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                current_hand_state = get_hand_state(hand_landmarks)

                if current_hand_state != prev_hand_state:
                    if current_hand_state == 'open':
                        command = 'O'
                        status_text = "Tangan Terbuka (Servo 90)"
                    else:
                        command = 'C'
                        status_text = "Tangan Tertutup (Servo 0)"

                    print(f"Mengirim '{command}' ke Arduino. Status: {status_text}")
                    if arduino:
                        try:
                            arduino.write(command.encode('utf-8'))
                        except serial.SerialException as e:
                            print(f"Error mengirim data serial: {e}")
                            arduino.close() # Close connection on error
                            arduino = None
                            messagebox.showerror("Serial Error", f"Komunikasi serial terputus: {e}")
                            is_running = False # Stop the main loop
                            break # Exit inner loop
                    prev_hand_state = current_hand_state
                else:
                    if prev_hand_state == 'open':
                        status_text = "Tangan Terbuka (Servo 90)"
                    elif prev_hand_state == 'closed':
                        status_text = "Tangan Tertutup (Servo 0)"
                    else:
                        status_text = "Menunggu deteksi tangan..."

        else:
            status_text = "Tidak ada tangan terdeteksi."
            if prev_hand_state is not None:
                print("Tangan hilang, reset status.")
                prev_hand_state = None

        cv2.putText(image, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
        cv2.imshow('Hand Pose Detection', image)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Tombol 'q' ditekan, mengakhiri program.")
            is_running = False # Set flag to stop the loop

    # Cleanup
    print("Membersihkan sumber daya...")
    if arduino:
        arduino.close()
        print("Koneksi serial ditutup.")
    if cap:
        cap.release()
    cv2.destroyAllWindows()
    print("Program Python selesai.")

# --- GUI for Port Selection ---
def get_available_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

def create_port_selection_window():
    port_window = tk.Toplevel(root) # Buat jendela baru
    port_window.title("Pilih Port Serial Arduino")
    port_window.geometry("350x150")
    port_window.resizable(False, False)

    # Label instruksi
    ttk.Label(port_window, text="Pilih port serial Arduino Anda:").pack(pady=10)

    # Dropdown menu untuk port
    ports = get_available_ports()
    if not ports:
        messagebox.showwarning("Tidak Ada Port", "Tidak ada port serial yang terdeteksi. Pastikan Arduino terhubung.")
        ports = ["Tidak Ada Port"] # Sediakan opsi dummy
        select_port_button.config(state="disabled") # Nonaktifkan tombol konfirmasi

    port_var = tk.StringVar(port_window)
    port_var.set(ports[0] if ports else "") # Set default value
    port_dropdown = ttk.Combobox(port_window, textvariable=port_var, values=ports, state="readonly")
    port_dropdown.pack(pady=5)

    def refresh_ports():
        new_ports = get_available_ports()
        port_dropdown['values'] = new_ports
        if new_ports:
            port_var.set(new_ports[0])
            select_port_button.config(state="normal")
        else:
            port_var.set("Tidak Ada Port")
            select_port_button.config(state="disabled")
        messagebox.showinfo("Refresh", "Daftar port telah diperbarui.")

    ttk.Button(port_window, text="Refresh Ports", command=refresh_ports).pack(pady=5)

    def on_confirm():
        selected_port = port_var.get()
        if selected_port == "Tidak Ada Port" or not selected_port:
            messagebox.showwarning("Pilihan Invalid", "Silakan pilih port yang valid.")
            return

        port_window.destroy() # Tutup jendela pemilihan port
        root.withdraw()      # Sembunyikan jendela utama Tkinter
        start_hand_pose_detection(selected_port) # Mulai deteksi tangan

    select_port_button = ttk.Button(port_window, text="Confirm and Start", command=on_confirm)
    select_port_button.pack(pady=10)

    # Nonaktifkan tombol jika tidak ada port
    if not ports or ports == ["Tidak Ada Port"]:
        select_port_button.config(state="disabled")

# --- Main Tkinter Root Window (for initial setup or hidden) ---
root = tk.Tk()
root.withdraw() # Sembunyikan jendela utama Tkinter saat startup

# Panggil fungsi untuk membuat jendela pemilihan port
create_port_selection_window()

# Jika jendela pemilihan port ditutup secara paksa, pastikan aplikasi keluar
root.protocol("WM_DELETE_WINDOW", lambda: root.destroy()) # Handle window close for root

root.mainloop()

# Pastikan semua sumber daya dibersihkan jika mainloop berhenti karena alasan lain
if arduino:
    arduino.close()
    print("Koneksi serial ditutup (dari cleanup akhir).")
if cap:
    cap.release()
    print("Kamera dilepaskan (dari cleanup akhir).")
cv2.destroyAllWindows()
