import streamlit as st
import os
import gspread
from google.oauth2.service_account import Credentials

# SendGrid imports
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Environment variables
from dotenv import load_dotenv

load_dotenv()
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")

# LLM call
from restaurant_graph import call_model

# Import your email templates
from emails_templates import asunto_1, mensaje_1_html, mensaje_1_plain

# Google Sheet ID (extracted from your provided URL)
SHEET_ID = "1KkUROgG1enUbg4KYEJhgmZ8sT7nGCCaN3p8w-mRfxmE"


# ----------------------------------------------------------
# Google Sheets Functions
# ----------------------------------------------------------
def get_gspread_client():
    json_path = os.getenv(
        "GOOGLE_CREDENTIALS_JSON", "data/spreadsheet-demo-for-hr-9cf643c81c21.json"
    )
    if os.path.exists(json_path):
        client = gspread.service_account(filename=json_path)
        return client
    else:
        creds_dict = st.secrets["GOOGLE_SERVICE_ACCOUNT"]
        creds = Credentials.from_service_account_info(
            creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        client = gspread.authorize(creds)
        return client


def get_sheet():
    client = get_gspread_client()
    sheet = client.open_by_key(SHEET_ID).sheet1
    return sheet


def get_restaurant_data(email):
    sheet = get_sheet()
    cell = sheet.find(email)
    if cell is None:
        return None
    row_values = sheet.row_values(cell.row)
    while len(row_values) < 6:
        row_values.append("")
    try:
        row_values[5] = int(row_values[5])
    except ValueError:
        row_values[5] = 0
    return row_values


def insert_placeholder_email(email):
    if get_restaurant_data(email) is None:
        sheet = get_sheet()
        new_row = [email, "", "", "", "", "0"]
        sheet.append_row(new_row)


def mark_form_completed(email, info_general, preguntas_frecuentes, info_adicional):
    """
    Updates the row for the given email with the full data and sets has_completed_form to 1.
    Note: The sheet currently has 5 data columns. Here we map:
      - Column2: información_general
      - Column3: preguntas_frecuentes
      - Column4: información_adicional
      - Column5: se deja vacío (puedes modificarlo según lo requieras)
    """
    sheet = get_sheet()
    try:
        cell = sheet.find(email)
        row_number = cell.row
        updated_row = [
            email,
            info_general,
            preguntas_frecuentes,
            info_adicional,
            "",  # Puedes dejar este campo vacío o asignarle otro valor
            "1",
        ]
        cell_range = f"A{row_number}:F{row_number}"
        sheet.update(cell_range, [updated_row])
    except gspread.exceptions.CellNotFound:
        new_row = [
            email,
            info_general,
            preguntas_frecuentes,
            info_adicional,
            "",
            "1",
        ]
        sheet.append_row(new_row)


# ----------------------------------------------------------
# Email Sending & Navigation Functions
# ----------------------------------------------------------
def enviar_correo(recipient, subject, html_content, plain_text=None):
    message = Mail(
        from_email="Alex de AutoFlujo Star <alex@autoflujo.com>",
        to_emails=recipient,
        subject=subject,
        html_content=html_content,
    )
    if plain_text:
        message.plain_text_content = plain_text

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"Email sent! Status Code: {response.status_code}")
        return response.status_code
    except Exception as e:
        print("Error:", str(e))
        return None


def go_to(page_name):
    st.session_state["page"] = page_name
    st.rerun()


# ----------------------------------------------------------
# Page Functions
# ----------------------------------------------------------
def pagina_home():
    st.title("Bienvenido a la Configuración de tu Agente IA")
    st.write("Por favor, ingresa tu correo electrónico para continuar.")

    email_input = st.text_input("Correo electrónico", key="home_email")

    if st.button("Continuar"):
        if email_input.strip():
            data = get_restaurant_data(email_input.strip())
            st.session_state["email"] = email_input.strip()
            if data:
                has_completed_form = data[5]
                if has_completed_form == 1:
                    go_to("chat")
                else:
                    go_to("formulario")
            else:
                status = enviar_correo(
                    recipient=email_input.strip(),
                    subject=asunto_1,
                    html_content=mensaje_1_html,
                    plain_text=mensaje_1_plain,
                )
                if status == 202:
                    st.success("¡Cargando tu información, espera un momento!")
                else:
                    st.warning("No se pudo enviar el correo de bienvenida.")
                insert_placeholder_email(email_input.strip())
                go_to("formulario")
        else:
            st.warning("Por favor, ingresa un correo válido.")


def pagina_formulario():
    if st.button("🔙 Regresar al Inicio"):
        st.session_state["email"] = ""
        go_to("home")

    st.title("Formulario de Configuración de tu Agente IA")
    st.write(
        "Completa la siguiente información para entrenar a tu Agente IA. "
        "Estará listo en segundos 😉"
    )
    st.write("Campos con * son obligatorios.")

    # 1. Información básica del restaurante
    st.subheader("1. Información básica del restaurante")
    info_nombre = st.text_input("Nombre del Restaurante *")
    info_tipo_cocina = st.text_input(
        "Tipo de Cocina (Ej.: italiana, mexicana, sushi...) *"
    )
    info_google_maps = st.text_input("Dirección (link Google Maps recomendado) *")
    info_horarios = st.text_area(
        "Horario de Servicio *",
        "Lunes a Viernes: 11:00 am - 10:00 pm\nSábado: 11:00 am - 12:00 am\nDomingos: 11:00 am - 9:00 pm",
    )
    info_contacto = st.text_input("Teléfono o WhatsApp para Reservaciones *")
    info_menu_link = st.text_input("Link al menú digital (Opcional)")

    def info_general_is_valid():
        return all(
            [
                info_nombre.strip(),
                info_tipo_cocina.strip(),
                info_google_maps.strip(),
                info_horarios.strip(),
                info_contacto.strip(),
            ]
        )

    info_general_str = f"""
**Nombre:** {info_nombre}
**Tipo de Cocina:** {info_tipo_cocina}
**Dirección:** {info_google_maps}
{"**Menú Digital:** " + info_menu_link if info_menu_link.strip() else ""}
**Horario:** {info_horarios}
**Contacto:** {info_contacto}
    """

    # 2. Preguntas frecuentes que responderá tu Agente IA
    st.subheader("2. Preguntas frecuentes que responderá tu Agente IA")
    servicio_entrega = st.text_area(
        "¿Tienen servicio para llevar (Pick Up) o domicilio? *\n(Explica brevemente cómo funciona)"
    )
    metodos_pago = st.text_area(
        "Métodos de pago aceptados *\n(Ej.: Efectivo, tarjetas, transferencias, etc.)",
        "Efectivo, Tarjeta",
    )
    promociones_eventos = st.text_area(
        "¿Ofrecen promociones especiales o paquetes para eventos?\n(Menciona brevemente las más importantes o escribe 'no aplica')"
    )
    permite_mascotas = st.selectbox(
        "¿Permiten ingreso con mascotas?", ["Sí", "No"], index=0
    )

    preguntas_frecuentes_str = f"""
**Servicio para llevar o domicilio:** {servicio_entrega}
**Métodos de Pago:** {metodos_pago}
**Promociones/Paquetes:** {promociones_eventos}
**Ingreso con Mascotas:** {permite_mascotas}
    """

    # 3. Información adicional importante
    st.subheader("3. Información adicional importante")
    info_adicional = st.text_area(
        "Si hay algún otro detalle importante que el Agente IA deba conocer, escríbelo aquí brevemente:\n(Ej.: estacionamiento, accesos especiales, días festivos especiales, etc.)"
    )

    if st.button("Enviar"):
        email_user = st.session_state.get("email", "")
        if not info_general_is_valid():
            st.warning("Todos los campos marcados con * son obligatorios.")
            return

        if email_user.strip():
            mark_form_completed(
                email_user.strip(),
                info_general_str,
                preguntas_frecuentes_str,
                (
                    info_adicional
                    if info_adicional.strip()
                    else "No se agregó información adicional."
                ),
            )
            st.success("¡Información guardada exitosamente!")
            go_to("chat")
        else:
            st.warning("No se detectó un correo válido. Regresa al inicio.")


def pagina_chat():
    st.title("Chatea con tu Agente IA")
    st.write(
        "Escribe en la barra inferior cualquier duda y tu Agente IA te responderá. "
        "Te guiará para que agendes una reservación en tu restaurante."
    )
    st.markdown(
        'Para revisar la información de tus reservaciones <a href="https://airtable.com/appWZExxj1q0LD4n1/shr2YO6pa1FtGtqMH/tbll5UzqzJG0f2YMJ?date=undefined&mode=undefined" target="_blank">da click en esta tabla</a>.',
        unsafe_allow_html=True,
    )
    st.markdown(
        """Si quieres instalar este Agente IA en el WhatsApp de tu negocio, 
    <a href="https://api.whatsapp.com/send/?phone=525559075128&text=Me+interesa+generar+rese%C3%B1as+positivas+en+mi+restaurante+con+AutoFlujo+Star.+%C2%BFMe+das+m%C3%A1s+informaci%C3%B3n%3F&type=phone_number&app_absent=0" 
    target="_blank">da click aquí</a>.""",
        unsafe_allow_html=True,
    )

    email_user = st.session_state.get("email", "")
    if not email_user:
        st.warning("No email found. Regresa al Inicio.")
        return

    data = get_restaurant_data(email_user.strip())
    if not data:
        st.warning("No hay datos en la hoja. Regresa al Inicio.")
        return

    restaurant_data = f"""--- RESTAURANT DATA ---
Información Básica:
{data[1]}

Preguntas Frecuentes:
{data[2]}

Información Adicional:
{data[3]}
-------------------------
"""

    config_dict = {"configurable": {"thread_id": email_user}}

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input := st.chat_input("Escribe tu mensaje..."):
        user_message = {"role": "user", "content": user_input}
        st.session_state["messages"].append(user_message)
        with st.chat_message("user"):
            st.markdown(user_input)

        response_text = call_model(
            messages=[{"role": "user", "content": user_input}],
            phone=email_user,
            restaurant_data=restaurant_data,
            config=config_dict,
        )
        assistant_message = {"role": "assistant", "content": response_text}
        st.session_state["messages"].append(assistant_message)
        with st.chat_message("assistant"):
            st.markdown(response_text)

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Regresar al Inicio"):
            go_to("home")
    with col2:
        st.markdown(
            '<a href="https://airtable.com/appWZExxj1q0LD4n1/shr2YO6pa1FtGtqMH/tbll5UzqzJG0f2YMJ?date=undefined&mode=undefined" target="_blank">'
            '<button style="width: 100%; padding: 0.6rem; background-color: #0072C6; color: white; border: none; cursor: pointer;">'
            "Ver Reservaciones</button></a>",
            unsafe_allow_html=True,
        )


def add_logo_and_footer():
    st.image("images/autoflujo-logo.png", width=150)
    st.markdown("<hr style='margin-top:3em'>", unsafe_allow_html=True)


def main():
    add_logo_and_footer()

    if "page" not in st.session_state:
        st.session_state["page"] = "home"

    page = st.session_state["page"]

    if page == "home":
        pagina_home()
    elif page == "formulario":
        pagina_formulario()
    elif page == "chat":
        pagina_chat()


if __name__ == "__main__":
    main()
