```[5V Netzteil / Step-Down]
        |
        +--> VIN Waveshare Board --> DC-Motoren (TB6612)
        +--> ULN2003 VCC ---------> Stepper (28BYJ-48)
        +--> Servo VCC ------------> SG92R
        |
       GND ------------------------+
                                   |
                        +----------+----------+
                        |                     |
                [Raspberry Pi Pico W]     [Alle Module]
                   (USB / VSYS)             (GND gemeinsam)```


### 🗲 Kostengünstiges Stromversorgungskonzept

*(1 × 230 V‑Stecker, versorgt alle Motoren + Pico‑W sicher)*

| Variante                   | Bauteil                                                                    | Daten & Preis (D‑/EU‑Straßenpreis) | Pro / Contra                                                                                           | Empfehlung                           |
| -------------------------- | -------------------------------------------------------------------------- | ---------------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------ |
| **A** (Ein­netzteil)       | **5 V / 10 A Schaltnetzteil**<br>‑ Mean Well RS‑50‑5<br>‑ Joy‑IT EPS‑65‑05 | 50 W, Schraubklemmen<br>10–15 €    | + nur 1 Gerät<br>+ intern geregelt/geschützt<br>+ Erdung möglich<br>− offenes Netzteil – Gehäuse nötig | **Beste Preis‑Leistung**             |
| **B** (Hutschiene)         | **DIN 5 V / 8 A** (z. B. HDR‑60‑5)                                         | 60 W, Hutschiene<br>17–20 €        | + saubere Montage<br>− Hutschine/Box nötig                                                             | ok, falls Schaltschrank vorhanden    |
| **C** (“Handy‑Ladegeräte”) | 2 × USB‑PD‑Netzteile (5 V / 3 A) + 1 × USB 5 V / 2 A                       | 3 × 6 € ≈ 18 €                     | + überall verfügbar<br>+ gleich Kabel<br>− 3× Steckdose<br>− keine Masse‑Klemme                        | nur wenn Gehäusefrei + steckdosen ok |
| **D** (PC‑Netzteil)        | Micro‑ATX PSU gebraucht                                                    | 5 V 15–20 A                        | + Spottbillig (5 – 10 €)<br>+ Lüfter schon drin<br>− groß, laut<br>− ATX‑Power‑On‑Hack nötig           | nur bei Platz & Lautstärke egal      |

---

## Dimensionierung

| Last             | Strom (Spitze)               | Reserve‑Faktor | Budgetiert  |
| ---------------- | ---------------------------- | -------------- | ----------- |
| 3 × 130‑DC‑Motor | 0,8 A ea. (\*Anlauf ≈ 1,5 A) | ×1,5           | 4 A         |
| 2 × 28BYJ + ULN  | 0,24 A ea.                   | ×1,2           | 0,6 A       |
| 3 × Servo SG90   | 0,7 A ea. (Stall)            | ×1,2           | 2,5 A       |
| Pico W + Boards  | 0,2 A                        | ×1             | 0,2 A       |
| **Summe**        |                              |                | **≈ 7,3 A** |

→ **5 V / 8 A min.**, besser 10 A.

---

## Empfohlene Umsetzung (Variante A)

1. **Mean Well RS‑50‑5**

   * 230 V → 5 V 10 A, \~12 €.
   * Schraubklemmen: L, N, PE / +5 V, GND.
2. **Verkabelung**

   * **+5 V** zu VIN des Waveshare‑Boards (speist DC‑Motoren).
   * **+5 V** weiterverteilt an ULN2003 + Servos (über 2,5 mm² Verteilklemme).
   * **Pico W**:

     * Entweder USB‑Netzteil (sauberste Trennung).
     * **Oder** zweite Leitung +1 000 µF Elko → VSYS, wenn nur ein Netzteil gewünscht.
3. **Entstörung**

   * Jeder Servo + Stepper: 100 nF KerKo zwischen VCC/GND.
   * DC‑Motoren: 100 nF Motoranschlüsse + 220 µF Elko am TB6612‐VIN.
4. **Gehäuse / Sicherheit**

   * RS‑50‑5 in gedrucktem oder Metall‑Kleingehäuse; PE (Schutzleiter) anschließen.
   * Primärseite abgedeckt, Lüftungsschlitze nach oben.
5. **Kosten**

   * Netzteil 12 €
   * Verteilklemmen, Elkos, Kabel ≈ 6 €
   * Gesamt **< 20 €** für komplette 230 V → 5 V 10 A‑Versorgung.

---

### Warum nicht mehrere Handy‑Netzteile?

* Kein gemeinsamer Massenknoten → mehr Gleichtakt­störungen.
* Mehr Steckdosen, mehr Kabelsalat.
* Trotz ähnlichem Preis weniger stabil bei Anlauf­strömen (OTP/OPP).

---

## Schnell‑Checkliste zum Aufbau

* [ ] Netzteil 5 V ≥ 10 A installiert & geerdet
* [ ] 2,5 mm² Haupt‑Versorgungs­kabel zu Motor‑/Servo‑Verteilung
* [ ] 470‑µF Elko nah am Waveshare‑VIN
* [ ] Separate 5 V‑Leitung (oder USB) für Pico W
* [ ] Sterne‑Ground: alle GND an einem Schraubklemmen­block
* [ ] Leitungs­querschnitte: Motor ≥ AWG 20, Servo AWG 24, Signal AWG 26–28
* [ ] Sicherung (z. B. 2 A träge) in Primär­leitung oder Polyfuse 8 A sekundär

Damit hast du eine **kostengünstige, nur 1× 230 V‑Stecker**‑Lösung, die alle Motoren und den Pico zuverlässig versorgt.
