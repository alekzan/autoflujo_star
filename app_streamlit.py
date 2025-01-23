import streamlit as st
import sqlite3
import os

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

DB_NAME = "data/restaurante_data.db"


# --------------------
# Ensure the table exists with 'has_completed_form' column
# --------------------
def create_table():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS restaurante_info(
            email TEXT PRIMARY KEY,
            informacion_general TEXT,
            politicas_metodos_pago TEXT,
            menu_restricciones TEXT,
            promociones_eventos TEXT,
            has_completed_form BOOLEAN DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()


create_table()


# --------------------
# Función para ENVIAR correo con SendGrid
# --------------------
def enviar_correo(recipient, subject, html_content, plain_text=None):
    """
    Sends an email using SendGrid API with optional Plain Text and HTML.
    """
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


# --------------------
# Obtener fila completa
# --------------------
def get_restaurant_data(email):
    """
    Returns the row if exists, else None.
    Row structure:
      (email, info_general, politicas_pago, menu_restricciones, promos, has_completed_form)
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        """
        SELECT email, informacion_general, politicas_metodos_pago, 
               menu_restricciones, promociones_eventos, has_completed_form
          FROM restaurante_info
         WHERE email=?
        """,
        (email,),
    )
    data = c.fetchone()
    conn.close()
    return data


# --------------------
# Insert or update minimal row for new email (if not exists)
# without the form data. has_completed_form=0
# --------------------
def insert_placeholder_email(email):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Only insert if it doesn't exist
    c.execute(
        """
        INSERT OR IGNORE INTO restaurante_info(
            email, informacion_general, politicas_metodos_pago,
            menu_restricciones, promociones_eventos, has_completed_form
        )
        VALUES (?, '', '', '', '', 0)
        """,
        (email,),
    )
    conn.commit()
    conn.close()


# --------------------
# Function to mark form as completed (has_completed_form=1)
# --------------------
def mark_form_completed(
    email, info_general, politicas_pago, menu_restricciones, promociones_eventos
):
    """
    Updates the row to store the full data and set has_completed_form=1
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        """
        UPDATE restaurante_info
           SET informacion_general=?,
               politicas_metodos_pago=?,
               menu_restricciones=?,
               promociones_eventos=?,
               has_completed_form=1
         WHERE email=?
        """,
        (info_general, politicas_pago, menu_restricciones, promociones_eventos, email),
    )
    conn.commit()
    conn.close()


# --------------------
# Cambiar de página
# --------------------
def go_to(page_name):
    st.session_state["page"] = page_name
    st.rerun()


# --------------------
# HOME
# --------------------
def pagina_home():
    st.title("Bienvenido a la Configuración de tu Agente IA")
    st.write("Por favor, ingresa tu correo electrónico para continuar.")

    email_input = st.text_input("Correo electrónico", key="home_email")

    if st.button("Continuar"):
        if email_input.strip():
            data = get_restaurant_data(email_input.strip())
            st.session_state["email"] = email_input.strip()

            # If email is found in DB
            if data:
                # data[5] = has_completed_form (0/1)
                has_completed_form = data[5]
                if has_completed_form == 1:
                    # Form was completed => go to chat
                    go_to("chat")
                else:
                    # Form incomplete => go to form
                    go_to("formulario")
            else:
                # Email not in DB => Send email once
                status = enviar_correo(
                    recipient=email_input.strip(),
                    subject=asunto_1,
                    html_content=mensaje_1_html,
                    plain_text=mensaje_1_plain,
                )
                if status == 202:
                    st.success("¡Correo de bienvenida enviado con éxito!")
                else:
                    st.warning("No se pudo enviar el correo de bienvenida.")

                # Insert placeholder row => has_completed_form=0
                insert_placeholder_email(email_input.strip())

                # Then go to form
                go_to("formulario")
        else:
            st.warning("Por favor, ingresa un correo válido.")


# --------------------
# FORMULARIO
# --------------------
def pagina_formulario():
    if st.button("🔙 Regresar al Inicio"):
        st.session_state["email"] = ""  # Clear stored email
        go_to("home")

    st.title("Formulario de Configuración de tu Agente IA")
    st.write(
        "Completa la siguiente información para entrenar a tu Agente IA. "
        "Estará listo en segundos 😉"
    )
    st.write("Campos con * son obligatorios.")

    # 1. Información General
    st.subheader("1. Información General del Restaurante")
    info_nombre = st.text_input("Nombre del Restaurante *")
    info_ubicacion = st.text_input("Ubicación (Dirección exacta) *")
    info_google_maps = st.text_input("Link de Google Maps *")
    info_menu_link = st.text_input("Enlace al Menú Digital (Opcional)")
    info_tipo_cocina = st.text_input("Tipo de Cocina (Italiana, Mexicana, etc.) *")
    info_contacto = st.text_input("Contacto para Clientes (Tel, WhatsApp, etc.) *")
    info_horarios = st.text_area(
        "Horario de Apertura y Cierre (ej: Lunes-Viernes 12:00-22:00) *",
        "Lunes-Viernes: \nSábados y Domingos: ",
    )
    info_dias_festivos = st.text_area(
        "Días Festivos (¿abren en festivos? Horarios especiales?) *"
    )

    def info_general_is_valid():
        return all(
            [
                info_nombre.strip(),
                info_ubicacion.strip(),
                info_google_maps.strip(),
                info_tipo_cocina.strip(),
                info_contacto.strip(),
                info_horarios.strip(),
                info_dias_festivos.strip(),
            ]
        )

    info_general_str = f"""
**Nombre:** {info_nombre}
**Ubicación:** {info_ubicacion}
**Google Maps:** {info_google_maps}
{"**Menú Online:** " + info_menu_link if info_menu_link.strip() else ""}
**Tipo de Cocina:** {info_tipo_cocina}
**Contacto:** {info_contacto}
**Horarios:** {info_horarios}
**Días Festivos:** {info_dias_festivos}
    """

    # 2. Políticas y Métodos de Pago
    st.subheader("2. Políticas y Métodos de Pago")
    metodos_pago = st.text_area(
        "Métodos de pago aceptados (Ej: Efectivo, Tarjeta)", "Efectivo, Tarjeta"
    )
    propinas_tarjeta = st.selectbox(
        "¿Aceptan propinas con tarjeta?", ["Sí", "No"], index=0
    )
    bebidas_pasteles_externos = st.text_input(
        "¿Se permite traer bebidas externas?", "No"
    )

    politicas_pago_str = f"""
**Métodos de Pago:** {metodos_pago}
**Propinas con Tarjeta:** {propinas_tarjeta}
**Bebidas/Pasteles Externos:** {bebidas_pasteles_externos}
    """

    # 3. Promociones y Eventos
    st.subheader("3. Promociones y Eventos")
    promos_diarias = st.text_area("¿Tienen promociones diarias?", "No actualmente")
    paquetes_celebracion = st.text_area(
        "¿Tienen paquetes para celebraciones?",
        "Sí, paquete con pastel y te cantamos las mañanitas.",
    )

    promociones_eventos_str = f"""
**Promociones Diarias:** {promos_diarias}
**Paquetes de Celebración:** {paquetes_celebracion}
    """

    if st.button("Enviar"):
        email_user = st.session_state.get("email", "")

        if not info_general_is_valid():
            st.warning("Todos los campos marcados con * son obligatorios.")
            return

        if email_user.strip():
            # Update row => set has_completed_form=1
            mark_form_completed(
                email_user.strip(),
                info_general_str,
                politicas_pago_str,
                "Información de menú no incluida",
                promociones_eventos_str,
            )
            st.success("¡Información guardada exitosamente!")
            go_to("chat")
        else:
            st.warning("No se detectó un correo válido. Regresa al inicio.")


# --------------------
# CHAT
# --------------------
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

    email_user = st.session_state.get("email", "")
    if not email_user:
        st.warning("No email found. Regresa al Inicio.")
        return

    data = get_restaurant_data(email_user.strip())
    if not data:
        st.warning("No hay datos en la BD. Regresa al Inicio.")
        return

    # data = (email, info_general, politicas, menu_restricciones, promos, has_completed_form)
    restaurant_data = f"""--- RESTAURANT DATA ---
Información General:
{data[1]}

Políticas y Métodos de Pago:
{data[2]}

Menú y Restricciones:
{data[3]}

Promociones y Eventos:
{data[4]}
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

    # 🔹 Buttons side by side
    col1, col2 = st.columns([1, 1])  # Two equal columns

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


# --------------------
# Agregar logo y footer para todas las páginas
# --------------------
def add_logo_and_footer():
    # Logo (top)
    st.image("images/autoflujo-logo.png", width=150)
    # Footer (bottom)
    st.markdown(
        "<hr style='margin-top:3em'>",
        unsafe_allow_html=True,
    )


# --------------------
# Control de Navegación
# --------------------
def main():
    # 1. Show logo at top
    add_logo_and_footer()  # This places the logo at the top and also the footer at the bottom

    # Because Streamlit re-runs top to bottom, the footer code will be placed
    # after all the page content. We'll re-inject it at the end too. We'll do a trick below.

    if "page" not in st.session_state:
        st.session_state["page"] = "home"

    page = st.session_state["page"]

    # 2. Show the chosen page
    if page == "home":
        pagina_home()
    elif page == "formulario":
        pagina_formulario()
    elif page == "chat":
        pagina_chat()


if __name__ == "__main__":
    main()
