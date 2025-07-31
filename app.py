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

def get_gesture_command(hand_landmarks):
    """
    Mendeteksi gestur tangan dan mengembalikan perintah yang sesuai.
    - V sign (2 jari) -> "ON"
    - 3 Jari -> "OFF"
    - Tangan Terbuka -> "O"
    - Tangan Tertutup -> "C"
    """
    # Helper untuk memeriksa apakah jari terbuka
    def is_finger_open(tip_index, pip_index):
        return hand_landmarks.landmark[tip_index].y < hand_landmarks.landmark[pip_index].y

    # Status jari individu
    index_open = is_finger_open(8, 7)
    middle_open = is_finger_open(12, 11)
    ring_open = is_finger_open(16, 15)
    pinky_open = is_finger_open(20, 19)
    thumb_open = hand_landmarks.landmark[4].x < hand_landmarks.landmark[3].x # Asumsi tangan kanan

    # 1. Cek gestur paling spesifik dulu (V dan 3 jari)
    # Gestur "V" (ON untuk Pin 8)
    if index_open and middle_open and not ring_open and not pinky_open:
        return "ON"
    # Gestur "Tiga Jari" (OFF untuk Pin 8)
    if index_open and middle_open and ring_open and not pinky_open:
        return "OFF"

    # 2. Cek gestur umum (terbuka/tertutup) jika gestur spesifik tidak ditemukan
    fingers_open_count = sum([index_open, middle_open, ring_open, pinky_open, thumb_open])
    
    # Gestur Tangan Terbuka (O untuk Pin 7)
    if fingers_open_count >= 4:
        return 'O'
    # Gestur Tangan Tertutup (C untuk Pin 7)
    else:
        return 'C'

# --- Main Application Logic (runs after port is selected) ---
def start_hand_pose_detection(selected_port):
    global arduino, cap, is_running, prev_hand_state

    try:
        arduino = serial.Serial(selected_port, 9600, timeout=1)
        print(f"Koneksi serial ke Arduino berhasil di port {selected_port}!")
        time.sleep(2)
    except serial.SerialException:
        messagebox.showerror("Error Serial", f"Gagal terhubung ke Arduino di {selected_port}.")
        return

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        messagebox.showerror("Error Kamera", "Gagal membuka kamera.")
        if arduino: arduino.close()
        return

    is_running = True
    prev_hand_state = None
    print("Program dimulai. Tekan 'q' untuk keluar.")

    while is_running and cap.isOpened():
        success, image = cap.read()
        if not success: break

        image = cv2.flip(image, 1)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = hands.process(image_rgb)

        status_text = "Arahkan tangan ke kamera"

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                current_command = get_gesture_command(hand_landmarks)

                if current_command and current_command != prev_hand_state:
                    command_to_send = current_command
                    
                    if command_to_send == "ON":
                        status_text = "on lamp"
                    elif command_to_send == "OFF":
                        status_text = "off lamp"
                    elif command_to_send == 'O':
                        status_text = "open pintu"
                    elif command_to_send == 'C':
                        status_text = "close"

                    print(f"Mengirim: '{command_to_send}' -> {status_text}")
                    if arduino:
                        try:
                            arduino.write(f"{command_to_send}\n".encode('utf-8'))
                        except serial.SerialException as e:
                            messagebox.showerror("Serial Error", f"Komunikasi serial terputus: {e}")
                            is_running = False
                            break
                    prev_hand_state = current_command

        else:
            prev_hand_state = None
            status_text = "Tidak ada tangan terdeteksi"

        cv2.putText(image, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
        cv2.imshow('Hand Pose Detection', image)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            is_running = False

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
