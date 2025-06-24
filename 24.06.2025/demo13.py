import cv2
import numpy as np
from collections import deque, Counter
import serial  # Arduino ile bağlantı için

# Arduino seri bağlantısı (port numarasını kendi sistemine göre değiştir!)
try:
    arduino = serial.Serial('COM5', 9600)  # Windows için COM port
    print("Arduino bağlantısı kuruldu.")
except:
    arduino = None
    print("Arduino bağlantısı BAŞARISIZ. Lütfen bağlantıyı kontrol et.")

Kp = 0.4
Ki = 0.0
Kd = 0.15
previous_error = 0
integral = 0
direction_history = deque(maxlen=5)
cap = cv2.VideoCapture(0)
exploration_mode = False
exploration_counter = 0

# --- PCA ile yön hesapla ---
def get_orientation(contour):
    sz = len(contour)
    data_pts = np.empty((sz, 2), dtype=np.float64)
    for i in range(sz):
        data_pts[i, 0] = contour[i, 0, 0]
        data_pts[i, 1] = contour[i, 0, 1]
    mean, eigenvectors, _ = cv2.PCACompute2(data_pts, mean=np.empty((0)))
    angle = np.arctan2(eigenvectors[0, 1], eigenvectors[0, 0])
    return np.degrees(angle)

# --- Kararı sabitle ---
def get_stable_direction(current_direction):
    direction_history.append(current_direction)
    return Counter(direction_history).most_common(1)[0][0]

# --- Motorlara manuel veri gönderme (sadece serial print) ---
def gonder_motor_verisi(direction):
    if arduino:
        try:
            arduino.write((direction + '\n').encode())  # örnek: "DUZ ILERLE\n"
        except:
            print("Arduino'ya yazılamadı")
    print(f"[Joystick Kontrol] Yön: {direction}")

# --- Ana döngü ---
def line_following():
    global previous_error, integral, exploration_mode, exploration_counter

    kernel = np.ones((5, 5), np.uint8)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        height, width, _ = frame.shape

        roi_top = height - 150
        roi_bottom = height
        roi_left = width // 2 - 100
        roi_right = width // 2 + 100
        roi_center_x = (roi_right - roi_left) // 2
        roi_center_global_x = (roi_left + roi_right) // 2

        roi = frame[roi_top:roi_bottom, roi_left:roi_right]

        blurred_roi = cv2.GaussianBlur(roi, (7, 7), 0)
        hsv_roi = cv2.cvtColor(blurred_roi, cv2.COLOR_BGR2HSV)
        lower_black = np.array([0, 0, 0])
        upper_black = np.array([180, 255, 90])
        mask_roi = cv2.inRange(hsv_roi, lower_black, upper_black)
        mask_roi = cv2.morphologyEx(mask_roi, cv2.MORPH_CLOSE, kernel, iterations=1)
        contours_roi, _ = cv2.findContours(mask_roi, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        min_area = 500
        filtered_roi = [cnt for cnt in contours_roi if cv2.contourArea(cnt) > min_area]

        blurred_frame = cv2.GaussianBlur(frame, (7, 7), 0)
        hsv_frame = cv2.cvtColor(blurred_frame, cv2.COLOR_BGR2HSV)
        mask_full = cv2.inRange(hsv_frame, lower_black, upper_black)
        mask_full = cv2.morphologyEx(mask_full, cv2.MORPH_CLOSE, kernel, iterations=1)
        contours_full, _ = cv2.findContours(mask_full, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        filtered_full = [cnt for cnt in contours_full if cv2.contourArea(cnt) > min_area]

        direction = "CIZGI YOK"
        found_line = False
        orientation_angle = None

        if filtered_roi:
            largest = max(filtered_roi, key=cv2.contourArea)
            M = cv2.moments(largest)
            if M["m00"] != 0:
                cx_roi = int(M["m10"] / M["m00"])
                cy_roi = int(M["m01"] / M["m00"])
                cx_global = cx_roi + roi_left
                cy_global = cy_roi + roi_top

                orientation_angle = get_orientation(largest)
                angle_deviation = abs(abs(orientation_angle) - 90)
                angle_tolerance = 15

                error = cx_roi - roi_center_x
                integral += error
                derivative = error - previous_error
                output = Kp * error + Ki * integral + Kd * derivative
                previous_error = error

                found_line = True
                exploration_mode = False
                exploration_counter = 0

                if angle_deviation < angle_tolerance:
                    if abs(error) < 30:
                        direction = "DUZ ILERLE"
                    else:
                        direction = "SOL KAY" if error < 0 else "SAG KAY"
                else:
                    if orientation_angle < -5:
                        direction = "SOL DON"
                    elif orientation_angle > 5:
                        direction = "SAG DON"
                    else:
                        direction = "DUZ ILERLE"

                cv2.drawContours(roi, [largest], -1, (0, 255, 0), 2)
                cv2.circle(frame, (cx_global, cy_global), 6, (0, 255, 0), -1)

        elif filtered_full:
            largest_full = max(filtered_full, key=cv2.contourArea)
            M_full = cv2.moments(largest_full)
            if M_full["m00"] != 0:
                cx_full = int(M_full["m10"] / M_full["m00"])
                cy_full = int(M_full["m01"] / M_full["m00"])

                error_outside = cx_full - roi_center_global_x
                found_line = True
                exploration_mode = False
                exploration_counter = 0

                if abs(error_outside) < 30:
                    direction = "DUZ ILERLE (ROI'YE YAKIN)"
                else:
                    direction = "SOL KAY (ROI'YE DON)" if error_outside < 0 else "SAG KAY (ROI'YE DON)"

                cv2.drawContours(frame, [largest_full], -1, (0, 165, 255), 2)
                cv2.circle(frame, (cx_full, cy_full), 8, (0, 165, 255), -1)

        else:
            found_line = False
            exploration_counter += 1
            if exploration_counter > 10:
                exploration_mode = True

        if exploration_mode:
            direction = "DON (CIZGI ARANIYOR)"

        stable_direction = get_stable_direction(direction)

        # --- SADECE JOYSTICK MODU İÇİN: Motorlara veri gönderme (otonom yok) ---
        gonder_motor_verisi(stable_direction)

        # --- Görüntüleme ---
        cv2.putText(frame, f"Yon: {stable_direction}", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        if orientation_angle is not None:
            cv2.putText(frame, f"Aci: {int(orientation_angle)} deg", (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        if found_line:
            if 'cx_global' in locals() and 'cy_global' in locals() and stable_direction != "DON (CIZGI ARANIYOR)":
                cv2.putText(frame, f"x: {cx_global}, y: {cy_global}", (30, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            elif 'cx_full' in locals() and 'cy_full' in locals():
                cv2.putText(frame, f"x: {cx_full}, y: {cy_full}", (30, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        cv2.rectangle(frame, (roi_left, roi_top), (roi_right, roi_bottom), (255, 0, 0), 2)
        cv2.imshow("Underwater Line Following", frame)
        cv2.imshow("ROI Mask", mask_roi)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    line_following()
