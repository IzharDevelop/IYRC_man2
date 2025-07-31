// Definisikan pin output
const int RELAY_D7 = 7; // Lampu untuk perintah pintu
const int RELAY_D8 = 8; // Lampu untuk perintah sensor CDS
const int RELAY_D6 = 6; // Lampu untuk sensor NTC
const int RELAY_D9 = 9; // Pompa untuk sensor air

// Definisikan pin input sensor analog
const int NTC_PIN = A0;   // Sensor NTC
const int WATER_SENSOR_PIN = A1; // Sensor Air
const int CDS_SENSOR_PIN = A3;  // Sensor CDS

// Variabel untuk waktu delay non-blocking
unsigned long d7_on_time = 0;
bool d7_active = false;

unsigned long d8_on_time_serial = 0;
bool d8_active_serial = false;

void setup() {
  // Inisialisasi pin output
  pinMode(RELAY_D7, OUTPUT);
  pinMode(RELAY_D8, OUTPUT);
  pinMode(RELAY_D6, OUTPUT);
  pinMode(RELAY_D9, OUTPUT);

  // Pastikan semua relay dalam kondisi OFF di awal
  digitalWrite(RELAY_D7, LOW);
  digitalWrite(RELAY_D8, LOW);
  digitalWrite(RELAY_D6, LOW);
  digitalWrite(RELAY_D9, LOW);

  // Mulai komunikasi serial
  Serial.begin(9600);
  //Serial.println("Sistem siap. Kirim 'O' atau 'C' melalui Serial Monitor.");
}

void loop() {
  // --- Penanganan Perintah Serial ---
  if (Serial.available()) {
    char command = Serial.read(); // Baca perintah dari Serial Monitor

    if (command == 'O' || command == 'o') {
      //Serial.println("Perintah 'O' diterima: Menyalakan lampu D7 selama 3 detik.");
      digitalWrite(RELAY_D7, HIGH); // Nyalakan lampu D7
      d7_on_time = millis(); // Catat waktu saat lampu dinyalakan
      d7_active = true;
    } else if (command == 'C' || command == 'c') {
      //Serial.println("Perintah 'C' diterima: Menyalakan lampu D8 selama 5 detik.");
      digitalWrite(RELAY_D8, HIGH); // Nyalakan lampu D8
      d8_on_time_serial = millis(); // Catat waktu saat lampu dinyalakan
      d8_active_serial = true;
    }
  }

  // Cek apakah lampu D7 sudah menyala selama 3 detik
  if (d7_active && (millis() - d7_on_time >= 3000)) {
    digitalWrite(RELAY_D7, LOW); // Matikan lampu D7
    //Serial.println("Lampu D7 mati.");
    d7_active = false;
  }

  // Cek apakah lampu D8 (dari serial) sudah menyala selama 5 detik
  if (d8_active_serial && (millis() - d8_on_time_serial >= 5000)) {
    digitalWrite(RELAY_D8, LOW); // Matikan lampu D8
    //Serial.println("Lampu D8 (dari serial) mati.");
    d8_active_serial = false;
  }

  // --- Penanganan Sensor NTC (Pin A0) ---
  int ntcValue = analogRead(NTC_PIN);
  //Serial.print("NTC Value: ");
  //Serial.println(ntcValue);

  if (ntcValue > 700) {
    digitalWrite(RELAY_D6, HIGH); // Nyalakan lampu D6
    //Serial.println("NTC > 200: Lampu D6 ON");
    delay(5000);
  } else {
    digitalWrite(RELAY_D6, LOW); // Matikan lampu D6
    //Serial.println("NTC <= 200: Lampu D6 OFF");
  }

  // --- Penanganan Sensor Air (Pin A1) ---
  int waterValue = analogRead(WATER_SENSOR_PIN);
  //Serial.print("Water Sensor Value: ");
  //Serial.println(waterValue);

  if (waterValue < 50) {
    digitalWrite(RELAY_D9, HIGH); // Nyalakan pompa D9
    //Serial.println("Water Sensor < 5: Pompa D9 ON");
  } else if (waterValue > 500) { // Jika nilai air di atas 500 (kemungkinan kering/penuh)
    digitalWrite(RELAY_D9, LOW);  // Matikan pompa D9
    //Serial.println("Water Sensor > 500: Pompa D9 OFF");
  }

  // --- Penanganan Sensor CDS (Pin A3) ---
  int cdsValue = analogRead(CDS_SENSOR_PIN);
  //Serial.print("CDS Sensor Value: ");
  //Serial.println(cdsValue);

  //if (cdsValue < 300) {
    // Pastikan lampu D8 tidak sedang diaktifkan oleh perintah serial ('C')
    // Ini penting agar perintah serial punya prioritas durasi
    //if (!d8_active_serial) {
        //digitalWrite(RELAY_D8, HIGH); // Nyalakan lampu D8
        //Serial.println("CDS < 300: Lampu D8 ON");
    //}
  //} else {
    // Pastikan lampu D8 tidak sedang diaktifkan oleh perintah serial ('C')
    //if (!d8_active_serial) {
        //digitalWrite(RELAY_D8, LOW); // Matikan lampu D8
        //Serial.println("CDS >= 300: Lampu D8 OFF");
    //}
  //}

  // Jeda singkat untuk stabilitas dan agar Serial Monitor tidak terlalu cepat
  delay(100);
}
