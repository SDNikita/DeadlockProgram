import cv2
import mediapipe as mp
import pyautogui
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils
cap = cv2.VideoCapture(0)

current_keys = {
    "w": False,
    "s": False,
    "a": False,
    "d": False,
    "f": False,
    "q": False,
    "z": False,
    "x": False,
    "e": False,
    "space": False, "shift": False

}

while True:
    success, img = cap.read()
    if not success:
        break
    # Отзеркаливаем видео
    img = cv2.flip(img, 1)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)

    if results.multi_hand_landmarks and results.multi_handedness:
        for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):

            # Рисуем скелет
            mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            lm = hand_landmarks.landmark

            # stop
            is_fist = (lm[8].y > lm[6].y) and (lm[12].y > lm[10].y) and \
                      (lm[16].y > lm[14].y) and (lm[20].y > lm[18].y)

            new_keys = {
                "w": False, "s": False, "a": False, "d": False,
                "f": False, "q": False, "e": False,"x": False, "z": False,"space": False, "shift": False
            }

            if is_fist:
                cv2.putText(img, "STOP", (150, 100),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
            else:
                index_up = lm[8].y < lm[6].y
                middle_up = lm[4].y < lm[8].y
                right_up = lm[5].y > lm[17].y
                left_up = lm[17].y > lm[5].y
                space_up = lm[4].x<lm[13].x
                shift_up =  lm[8].y < lm[6].y and lm[12].y < lm[10].y and lm[16].y < lm[14].y and lm[20].y < lm[18].y and lm[4].x < lm[8].x

                second_ability = (lm[12].y>lm[10].y and lm[16].y>lm[14].y and lm[8].y>lm[6].y)
                first_ability = (lm[12].y>lm[10].y and lm[16].y>lm[14].y)
                third_ability = (lm[20].y>lm[18].y and lm[16].y>lm[14].y )
                four_ability = (lm[16].y>lm[13].y)

                if second_ability:
                    new_keys["e"] = True
                elif first_ability:
                    new_keys["f"] = True
                elif third_ability:
                    new_keys["z"] = True
                elif four_ability:
                    new_keys["x"] = True
                elif space_up:
                    new_keys["space"] = True
                elif shift_up:
                    new_keys["shift"] = True
                    new_keys["w"] = True
                elif index_up:
                    new_keys["w"] = True
                elif middle_up:
                    new_keys["s"] = True
                elif right_up:
                    new_keys["a"] = True
                elif left_up:
                    new_keys["d"] = True

            for key in ["w", "s", "a", "d", "f", "q", "e","z","x","space","shift"]:
                if new_keys[key] and not current_keys[key]:
                    pyautogui.keyDown(key)
                    print(f"НАЖАТА: [{key.upper()}]")
                elif not new_keys[key] and current_keys[key]:
                    pyautogui.keyUp(key)
                    print(f"ОТПУЩЕНА: [{key.upper()}]")
            # --- ВЫВОД В КОНСОЛЬ  ---
            for key in ["w", "s", "a", "d", "f","e","z","x", "space","shift"]:
                if new_keys[key] and not current_keys[key]:
                    print(f"НАЖАТА: [{key}]")
                elif not new_keys[key] and current_keys[key]:
                    print(f"ОТПУЩЕНА: [{key}]")
            # Обновляем состояния
            current_keys.update(new_keys)
            active_keys = [k.upper() for k, v in current_keys.items() if v]
            cv2.putText(img, f"Active Keys: {', '.join(active_keys)}", (10, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow("Hand Control - KEYBOARD ONLY", img)
    if cv2.waitKey(1) & 0xFF == ord(']'):
        break
cap.release()
cv2.destroyAllWindows()