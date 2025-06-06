import cv2
import mediapipe as mp
import time
import datetime
import requests # Para chamadas API
import geocoder # Para obter localização baseada no IP

# --- Constantes para simulação e logs ---
LOG_FILENAME = "emergency_log.txt"
API_ENDPOINT_GPS_SIMULADO = "http://127.0.0.1:8000/reportar_localizacao" # Endpoint da API (simulado)

# Inicialização
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_face = mp.solutions.face_mesh

hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
face_mesh = mp_face.FaceMesh(max_num_faces=1, min_detection_confidence=0.5)

# Histórico de mensagens na tela
mensagens_tela = []

# Para detectar toques rápidos (👆👆)
toque_anterior = 0
ultimo_toque = 0

# --- Funções de Logging e Comunicação ---

def gerar_log_arquivo(log_entry):
    """Salva uma entrada de log em um arquivo de texto."""
    try:
        with open(LOG_FILENAME, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    except Exception as e:
        print(f"[ERRO LOG] Não foi possível escrever no arquivo de log: {e}")

def registrar_mensagem(msg, tipo_alerta=None):
    """Registra a mensagem, exibe na tela, salva em log e envia alertas para a API se aplicável."""
    agora = datetime.datetime.now()
    hora_data = agora.strftime("%H:%M:%S // %d/%m/%Y")
    log_completo = f"[{hora_data}] {msg}"
    
    mensagens_tela.append(log_completo)
    print(log_completo)
    gerar_log_arquivo(log_completo)

    # Se qualquer tipo de alerta for fornecido, um relatório de localização será enviado para a API.
    if tipo_alerta:
        motivo_api = f"Status Report: {msg}" # Mensagem padrão para a API
        
        # Personaliza a mensagem para alertas críticos
        if tipo_alerta == "SOCORRO":
            motivo_api = f"Necessidade de socorro URGENTE: {msg}"
        
        elif tipo_alerta == "RISCO":
            motivo_api = f"Situação de risco detectada: {msg}"

        # Envia coordenadas para a API para qualquer alerta (SOCORRO, RISCO, INFO)
        enviar_coordenadas_gps_api(motivo_api, tipo_alerta=tipo_alerta)

def obter_coordenadas_gps():
    """Obtém as coordenadas GPS aproximadas com base no IP."""
    try:
        g = geocoder.ip('me')
        if g.ok and g.latlng:
            return g.latlng # Retorna uma lista [latitude, longitude]
        else:
            registrar_mensagem("Log GPS: Não foi possível obter coordenadas GPS via geocoder.")
            return None
    except Exception as e:
        registrar_mensagem(f"Log GPS: Erro ao tentar obter coordenadas: {e}")
        return None

def enviar_coordenadas_gps_api(motivo_alerta="Localização de emergência", tipo_alerta="INDEFINIDO"):
    """Obtém as coordenadas GPS, cidade/estado e simula o envio para uma API."""
    try:
        g = geocoder.ip('me')
        if g.ok and g.latlng:
            latitude, longitude = g.latlng
            cidade = g.city if g.city else "Desconhecida"
            estado = g.state if g.state else "Desconhecido"
            country = g.country if g.country else "Desconhecido"
        else:
            registrar_mensagem("Log GPS: Não foi possível obter dados de localização via geocoder.")
            return
    except Exception as e:
        registrar_mensagem(f"Log GPS: Erro ao tentar obter localização: {e}")
        return

    payload = {
        "latitude": latitude,
        "longitude": longitude,
        "cidade": cidade,
        "estado": estado,
        "pais": country,
        "tipo_alerta": tipo_alerta,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "origem": "SafeMeshApp",
        "motivo": motivo_alerta,
        "nivel_confianca_localizacao": "IP-based (aproximada)"
    }

    log_api = (f"--- SIMULAÇÃO API GPS ---\n"
               f"Enviando para: {API_ENDPOINT_GPS_SIMULADO}\n"
               f"Dados: {payload}\n"
               f"-------------------------")
    print(log_api)
    gerar_log_arquivo(f"[{time.strftime('%H:%M:%S')}] {log_api.replace('\n', ' | ')}")

    try:
        response = requests.post(API_ENDPOINT_GPS_SIMULADO, json=payload, timeout=10)
        response.raise_for_status()
        registrar_mensagem(f"Log API: Dados enviados com sucesso! Status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        registrar_mensagem(f"Log API: Erro ao enviar para API: {e}")


# --- Funções de Detecção ---

def detectar_gesto_mao(landmarks):
    """Detecta o gesto da mão e retorna a mensagem e o tipo de alerta correspondente."""
    global toque_anterior, ultimo_toque

    dedos = {
        "indicador": landmarks[8].y < landmarks[6].y,
        "medio": landmarks[12].y < landmarks[10].y,
        "anelar": landmarks[16].y < landmarks[14].y,
        "mindinho": landmarks[20].y < landmarks[18].y
    }
    
    # Lógica do polegar ajustada para diferenciar mão esquerda/direita
    if landmarks[2].x < landmarks[17].x: # Mão direita (palma para a câmera)
        dedos["polegar"] = landmarks[4].x < landmarks[3].x
    else: # Mão esquerda (ou dorso da direita)
        dedos["polegar"] = landmarks[4].x > landmarks[3].x

    if all(dedos.values()):
        return "✋ Preciso de ajuda", "RISCO"

    if dedos["polegar"] and not any([dedos["indicador"], dedos["medio"], dedos["anelar"], dedos["mindinho"]]):
        return "👍 Estou bem", "INFO"

    if dedos["polegar"] and dedos["mindinho"] and not any([dedos["indicador"], dedos["medio"], dedos["anelar"]]):
        return "🤙 Energia restabelecida", "INFO"

    if dedos["indicador"] and not any([dedos["medio"], dedos["anelar"], dedos["mindinho"], dedos["polegar"]]):
        tempo_atual = time.time()
        if tempo_atual - ultimo_toque < 0.5:
            if tempo_atual - toque_anterior > 2.0:
                toque_anterior = tempo_atual
                return "👆👆 Sinal de socorro ATIVADO", "SOCORRO"
        ultimo_toque = tempo_atual
    
    return None, None


def detectar_expressao(landmarks):
    """Detecta expressão de pânico e retorna a mensagem e o tipo de alerta."""
    largura_rosto = abs(landmarks[454].x - landmarks[234].x)
    if largura_rosto == 0: return None, None

    abertura_boca = (landmarks[14].y - landmarks[13].y) / largura_rosto
    abertura_olho_dir = abs(landmarks[145].y - landmarks[159].y) / largura_rosto
    abertura_olho_esq = abs(landmarks[374].y - landmarks[386].y) / largura_rosto
    
    limiar_boca_aberta = 0.07
    limiar_olhos_arregalados = 0.06

    if abertura_boca > limiar_boca_aberta and (abertura_olho_dir > limiar_olhos_arregalados or abertura_olho_esq > limiar_olhos_arregalados):
        return "😦 Situação de risco", "RISCO"
    return None, None


# --- Loop Principal da Webcam ---
cap = cv2.VideoCapture(0)

registrar_mensagem("Sistema SafeMesh iniciado. Monitorando gestos e expressões.")
busca_iniciada = False

def on_mouse_click(event, x, y, flags, param):
    global busca_iniciada
    if event == cv2.EVENT_LBUTTONDOWN:
        if not busca_iniciada and 10 <= x <= 200 and 10 <= y <= 60:
            busca_iniciada = True
            registrar_mensagem("Busca por gestos iniciada pelo usuário.")

cv2.namedWindow("SafeMesh - Visao de Emergencia")
cv2.setMouseCallback("SafeMesh - Visao de Emergencia", on_mouse_click)

while cap.isOpened():
    sucesso, frame = cap.read()
    if not sucesso:
        registrar_mensagem("Falha ao capturar frame da webcam.")
        break

    frame = cv2.flip(frame, 1)
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    if not busca_iniciada:
        cv2.rectangle(frame, (10, 10), (200, 60), (0, 255, 0), -1)
        cv2.putText(frame, "Iniciar Busca", (25, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    
    else:
        # Processar mãos
        resultado_mao = hands.process(img_rgb)
        if resultado_mao.multi_hand_landmarks:
            for mao_landmarks in resultado_mao.multi_hand_landmarks:
                gesto, tipo_alerta = detectar_gesto_mao(mao_landmarks.landmark)
                if gesto:
                    registrar_mensagem(f"Gesto: {gesto}", tipo_alerta=tipo_alerta)
                
                mp_drawing.draw_landmarks(frame, mao_landmarks, mp_hands.HAND_CONNECTIONS)

        # Processar rosto
        resultado_rosto = face_mesh.process(img_rgb)
        if resultado_rosto.multi_face_landmarks:
            for rosto_landmarks in resultado_rosto.multi_face_landmarks:
                expressao, tipo_alerta = detectar_expressao(rosto_landmarks.landmark)
                if expressao:
                    registrar_mensagem(f"Expressão: {expressao}", tipo_alerta=tipo_alerta)
                
                mp_drawing.draw_landmarks(
                    image=frame,
                    landmark_list=rosto_landmarks,
                    connections=mp_face.FACEMESH_TESSELATION,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=mp_drawing.DrawingSpec(thickness=1, circle_radius=1, color=(0,200,0))
                )

    # Mostrar últimas mensagens na tela
    for i, msg_tela in enumerate(mensagens_tela[-4:]):
        cv2.putText(frame, msg_tela, (10, frame.shape[0] - 110 + i * 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)

    cv2.imshow("SafeMesh - Visao de Emergencia", frame)

    if cv2.waitKey(5) & 0xFF == 27:  # ESC
        registrar_mensagem("Sistema SafeMesh finalizado pelo usuário.")
        break

cap.release()
cv2.destroyAllWindows()