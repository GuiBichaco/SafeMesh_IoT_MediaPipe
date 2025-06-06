import cv2
import mediapipe as mp
import time

# Inicialização
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_face = mp.solutions.face_mesh

hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
face_mesh = mp_face.FaceMesh(max_num_faces=1, min_detection_confidence=0.5)

# Histórico de mensagens
mensagens = []

# Para detectar toques rápidos (👆👆)
toque_anterior = 0
ultimo_toque = 0

# Função para registrar mensagem com horário
def registrar_mensagem(msg):
    hora = time.strftime("%H:%M:%S")
    mensagens.append(f"[{hora}] {msg}")
    print(f"[{hora}] {msg}")

# Detectar gestos
def detectar_gesto_mao(landmarks):
    global toque_anterior, ultimo_toque

    # Coordenadas dos dedos
    dedos = {
        "polegar": landmarks[4].x < landmarks[3].x,
        "indicador": landmarks[8].y < landmarks[6].y,
        "medio": landmarks[12].y < landmarks[10].y,
        "anelar": landmarks[16].y < landmarks[14].y,
        "mindinho": landmarks[20].y < landmarks[18].y
    }

    # ✋ Todos dedos levantados
    if all(dedos.values()):
        return "✋ Preciso de ajuda"

    # 👍 Joinha (só polegar levantado)
    if dedos["polegar"] and not any([dedos["indicador"], dedos["medio"], dedos["anelar"], dedos["mindinho"]]):
        return "👍 Estou bem"

    # 🤙 Hang loose (polegar + mindinho)
    if dedos["polegar"] and dedos["mindinho"] and not any([dedos["indicador"], dedos["medio"], dedos["anelar"]]):
        return "🤙 Energia restabelecida"

    # 👆👆 Dois toques rápidos com o indicador
    if dedos["indicador"] and not dedos["medio"]:
        tempo_atual = time.time()
        if tempo_atual - ultimo_toque < 0.4:  # dois toques em menos de 0.4s
            if tempo_atual - toque_anterior > 2:  # prevenir spam
                toque_anterior = tempo_atual
                return "🚨 Enviar sinal de socorro"
        ultimo_toque = tempo_atual

    return None

# Detectar expressões faciais
def detectar_expressao(landmarks):
    boca_aberta = landmarks[14].y - landmarks[13].y > 0.03
    olhos_arregalados = landmarks[159].y - landmarks[145].y > 0.03
    if boca_aberta and olhos_arregalados:
        return "😦 Situação de risco"
    return None

# Webcam
cap = cv2.VideoCapture(0)

while cap.isOpened():
    sucesso, frame = cap.read()
    if not sucesso:
        break

    frame = cv2.flip(frame, 1)
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    resultado_mao = hands.process(img_rgb)
    resultado_rosto = face_mesh.process(img_rgb)

    if resultado_mao.multi_hand_landmarks:
        for mao in resultado_mao.multi_hand_landmarks:
            gesto = detectar_gesto_mao(mao.landmark)
            if gesto:
                registrar_mensagem(f"Gesto: {gesto}")
            mp_drawing.draw_landmarks(frame, mao, mp_hands.HAND_CONNECTIONS)

    if resultado_rosto.multi_face_landmarks:
        for rosto in resultado_rosto.multi_face_landmarks:
            expressao = detectar_expressao(rosto.landmark)
            if expressao:
                registrar_mensagem(f"Expressão: {expressao}")
            mp_drawing.draw_landmarks(frame, rosto, mp_face.FACEMESH_TESSELATION)

    # Mostrar últimas mensagens
    for i, msg in enumerate(mensagens[-4:]):
        cv2.putText(frame, msg, (10, 30 + i * 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)

    cv2.imshow("SafeMesh - Visão de Emergência", frame)

    if cv2.waitKey(5) & 0xFF == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()
