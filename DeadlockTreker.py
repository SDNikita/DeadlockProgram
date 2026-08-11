import cv2
import mediapipe as mp
import pydirectinput
import ctypes
import keyboard
import numpy as np
import time

# Настройки для игры
pydirectinput.PAUSE = 0
ctypes.windll.shcore.SetProcessDpiAwareness(1)

JOY_DEADZONE = 0.08  # Мертвая зона для WASD

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)

base_hand_x, base_hand_y = 0.5, 0.5

current_keys = {
    "w": False, "s": False, "a": False, "d": False,
    "f": False, "q": False, "l": False, "i": False,
    "e": False, "space": False, "shift": False, "z": False ,"c": False ,"2": False, "3": False
}

prev_time = time.time()



while True:
    success, img = cap.read()
    if not success: break

    img = cv2.flip(img, 1)
    h_img, w_img, _ = img.shape
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    results = hands.process(img_rgb)

    # калибровка
    if keyboard.is_pressed('j'):
        if results.multi_hand_landmarks:
            palm = results.multi_hand_landmarks[0].landmark[9]
            base_hand_x, base_hand_y = palm.x, palm.y
            print(f"ЦЕНТР РУКИ: {base_hand_x:.2f}, {base_hand_y:.2f}")

    new_keys = {k: False for k in current_keys}

    if results.multi_hand_landmarks:
        hand_lms = results.multi_hand_landmarks[0]
        mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)
        lm = hand_lms.landmark

        # стоп
        is_fist = (lm[8].y > lm[6].y) and (lm[12].y > lm[10].y) and \
                  (lm[16].y > lm[14].y) and (lm[20].y > lm[18].y  )
        thumb_is_highest = (lm[4].y < lm[8].y and lm[4].y < lm[12].y and
                            lm[4].y < lm[16].y and lm[4].y < lm[20].y)

        if is_fist:
            new_keys["q"] = True
        else:
            #  WASD
            palm_x, palm_y = lm[9].x, lm[9].y
            joy_dx = palm_x - base_hand_x
            joy_dy = palm_y - base_hand_y

            # Вперед/Назад (Ось Y)
            if joy_dy < -JOY_DEADZONE:
                new_keys["w"] = True
            elif joy_dy > JOY_DEADZONE:
                new_keys["s"] = True

            # Влево/Вправо (Ось X)
            if joy_dx < -JOY_DEADZONE:
                new_keys["a"] = True
            elif joy_dx > JOY_DEADZONE:
                new_keys["d"] = True

            # жесты
            space_up = lm[4].x < lm[13].x
            shift_up = lm[8].y < lm[6].y and lm[12].y < lm[10].y and \
                       lm[16].y < lm[14].y and lm[20].y < lm[18].y and \
                       lm[4].x < lm[8].x

            second_ability = (lm[12].y > lm[10].y and lm[16].y > lm[14].y and lm[8].y > lm[6].y)
            first_ability = (lm[12].y > lm[10].y and lm[16].y > lm[14].y)
            third_ability = (lm[20].y > lm[18].y and lm[16].y > lm[14].y)
            four_ability = (lm[16].y > lm[13].y)

            first_item = lm[4].y<lm[8].y and lm[12].x<lm[10].x and lm[16].x<lm[14].x and lm[20].x<lm[18].x
            second_item =lm[4].y<lm[8].y and  lm[16].x<lm[14].x and lm[20].x<lm[18].x
            third_item =lm[4].y<lm[8].y and lm[20].x<lm[18].x
            four_item =lm[4].y<lm[8].y
            if thumb_is_highest:
                if first_item:
                    new_keys["z"] = True
                elif second_item:
                    new_keys["c"] = True
                elif third_item:
                    new_keys["2"] = True
                elif four_item:
                    new_keys["3"] = True
            else:
                # Привязка способностей
                if second_ability:
                    new_keys["e"] = True
                elif first_ability:
                    new_keys["f"] = True
                elif third_ability:
                    new_keys["l"] = True
                elif four_ability:
                    new_keys["i"] = True

            # Привязка атлетики
            if space_up: new_keys["space"] = True
            if shift_up: new_keys["shift"] = True


    for key in current_keys.keys():
        if new_keys[key] and not current_keys[key]:
            pydirectinput.keyDown(key)
            print(f"НАЖАТА: [{key.upper()}]")
        elif not new_keys[key] and current_keys[key]:
            pydirectinput.keyUp(key)
            print(f"ОТПУЩЕНА: [{key.upper()}]")

    current_keys.update(new_keys)


    curr_time = time.time()
    fps = 1 / (curr_time - prev_time)
    prev_time = curr_time

    # FPS
    cv2.putText(img, f"FPS: {int(fps)}", (w_img - 110, 30), 1, 1.5, (255, 0, 255), 2)

    #  Активные клавиши
    active = [k.upper() for k, v in current_keys.items() if v]
    cv2.putText(img, f"Active Keys: {', '.join(active)}", (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # рука
    cv2.circle(img, (int(base_hand_x * w_img), int(base_hand_y * h_img)), 20, (0, 255, 255), 2)
    if results.multi_hand_landmarks:
        cv2.circle(img, (int(lm[9].x * w_img), int(lm[9].y * h_img)), 5, (0, 0, 255), -1)

    cv2.imshow("Hand Control HUD", img)

    if cv2.waitKey(1) & 0xFF == ord(']'):
        for k in current_keys: pydirectinput.keyUp(k)
        break

cap.release()
cv2.destroyAllWindows()