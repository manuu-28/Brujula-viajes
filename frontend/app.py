"""Frontend de Brújula Viajes (Streamlit)."""
import os
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")
st.set_page_config(page_title="Brújula Viajes", page_icon="🧭", layout="wide")


def api(metodo: str, ruta: str, **kw):
    """Devuelve (ok, datos). Nunca lanza excepción: los errores se muestran al usuario."""
    try:
        r = requests.request(metodo, f"{API_URL}{ruta}", timeout=20, **kw)
    except requests.RequestException:
        return False, f"No hay conexión con la API en {API_URL}. ¿Está corriendo uvicorn?"
    try:
        datos = r.json()
    except ValueError:
        datos = {"detail": r.text}
    if r.ok:
        return True, datos
    return False, mensaje_error(r.status_code, datos)


def mensaje_error(status: int, datos) -> str:
    detalle = datos.get("detail", datos) if isinstance(datos, dict) else datos
    if status == 422 and isinstance(detalle, list):
        partes = []
        for e in detalle:
            campo = " → ".join(str(x) for x in e.get("loc", []) if x != "body")
            partes.append(f"• {campo}: {e.get('msg')}")
        detalle = "\n".join(partes)
    titulo = {409: "No se pudo completar (regla de negocio / sin cupo)", 422: "Datos inválidos",
              404: "No encontrado"}.get(status, f"Error {status}")
    return f"**{titulo}**\n\n{detalle}"


def mostrar(ok: bool, datos, exito: str | None = None) -> bool:
    if ok:
        if exito:
            st.success(exito)
    else:
        st.error(datos)
    return ok


def pesos(x) -> str:
    return f"${x:,.0f}".replace(",", ".")


def fecha(txt: str, con_hora: bool = True) -> str:
    try:
        d = datetime.fromisoformat(txt)
        return d.strftime("%Y-%m-%d %H:%M" if con_hora else "%Y-%m-%d")
    except (TypeError, ValueError):
        return str(txt)


@st.cache_data(ttl=60)
def cargar(ruta: str):
    ok, datos = api("GET", ruta)
    return datos if ok else []


ciudades = cargar("/ciudades/")
asesores = cargar("/asesores/")
IATAS = [c["iata"] for c in ciudades] if isinstance(ciudades, list) else []
NOMBRE_CIUDAD = {c["iata"]: c["nombre"] for c in ciudades} if isinstance(ciudades, list) else {}

st.sidebar.title("🧭 Brújula Viajes")
if not asesores:
    st.sidebar.error(f"No hay conexión con la API ({API_URL}) o no hay asesores cargados.")
    st.stop()
asesor = st.sidebar.selectbox("Usuario de la aplicación (asesor)", asesores,
                              format_func=lambda a: f"{a['nombre']} ({a['usuario']})")
USUARIO = asesor["usuario"]
modulo = st.sidebar.radio("Módulo", ["Buscar y reservar", "Reservas", "Catálogo y clientes", "Reportes"])
st.sidebar.caption(f"API: {API_URL}")

if "carrito" not in st.session_state:
    st.session_state.carrito = []


def agregar(item: dict, etiqueta: str):
    st.session_state.carrito.append({"item": item, "etiqueta": etiqueta})
    st.toast(f"Agregado: {etiqueta}")


def ciudad_select(etiqueta: str, key: str, vacia: bool = True):
    opciones = ([""] if vacia else []) + IATAS
    return st.selectbox(etiqueta, opciones, key=key,
                        format_func=lambda i: f"{NOMBRE_CIUDAD.get(i, '')} ({i})" if i else "Todas")


if modulo == "Buscar y reservar":
    st.header("Buscar y reservar")
    t_vuelos, t_hoteles, t_tours, t_paquetes = st.tabs(["✈️ Vuelos", "🏨 Hoteles", "🧭 Tours", "🎁 Paquetes"])

    with t_vuelos:
        c1, c2, c3 = st.columns(3)
        with c1:
            o = ciudad_select("Origen", "v_o")
        with c2:
            d = ciudad_select("Destino", "v_d")
        with c3:
            filtrar = st.checkbox("Filtrar por fecha", key="v_ff")
            f = st.date_input("Fecha", date.today() + timedelta(days=3), key="v_f", disabled=not filtrar)
        params = {k: v for k, v in {"origen": o, "destino": d, "fecha": f.isoformat() if filtrar else None}.items() if v}
        ok, vuelos = api("GET", "/vuelos/", params=params)
        if mostrar(ok, vuelos) and vuelos:
            st.dataframe(pd.DataFrame([{
                "Código": v["codigo"], "Aerolínea": v["aerolinea"], "Ruta": f"{v['origen']['iata']} → {v['destino']['iata']}",
                "Salida": fecha(v["salida"]), "Llegada": fecha(v["llegada"]),
                **{f"{t['tipo']}": f"{pesos(t['precio'])} · {t['sillas_disponibles']} sillas" for t in v["tarifas"]}}
                for v in vuelos]), hide_index=True, width="stretch")
            with st.form("f_vuelo"):
                c1, c2, c3 = st.columns(3)
                v = c1.selectbox("Vuelo", vuelos, format_func=lambda v: f"{v['codigo']} {v['origen']['iata']}→{v['destino']['iata']} {fecha(v['salida'])}")
                tarifa = c2.selectbox("Tarifa", ["Básica", "Clásica", "Flexible"])
                n = c3.number_input("Sillas", 1, 20, 1)
                if st.form_submit_button("Agregar al carrito"):
                    agregar({"tipo": "vuelo", "vuelo_codigo": v["codigo"], "tarifa": tarifa, "cantidad": int(n)},
                            f"Vuelo {v['codigo']} · {tarifa} × {n}")
        elif ok:
            st.info("No hay vuelos para ese filtro.")

    with t_hoteles:
        c1, c2, c3 = st.columns(3)
        with c1:
            ciu = ciudad_select("Ciudad", "h_c")
        with c2:
            entrada = st.date_input("Entrada", date.today() + timedelta(days=5), key="h_e")
        with c3:
            noches = st.number_input("Noches", 1, 30, 2, key="h_n")
        ok, hoteles = api("GET", "/hoteles/", params={k: v for k, v in
                                                      {"ciudad": ciu, "entrada": entrada.isoformat(), "noches": noches}.items() if v})
        if mostrar(ok, hoteles) and hoteles:
            filas = [{"Hotel": h["nombre"], "Ciudad": h["ciudad"]["nombre"], "★": h["categoria"], "Habitación": th["tipo"],
                      "Capacidad": th["capacidad"], "Precio/noche": pesos(th["precio_noche"]),
                      f"Libres las {noches} noches": th["libres_en_rango"], "Servicios": ", ".join(h["servicios"])}
                     for h in hoteles for th in h["tipos_habitacion"]]
            st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")
            mapa = pd.DataFrame([{"lat": h["ubicacion"]["coordinates"][1], "lon": h["ubicacion"]["coordinates"][0]} for h in hoteles])
            with st.expander("Ver en el mapa"):
                st.map(mapa)
            with st.form("f_hotel"):
                c1, c2, c3 = st.columns(3)
                h = c1.selectbox("Hotel", hoteles, format_func=lambda h: f"{h['nombre']} ({h['ciudad']['iata']})")
                tipo = c2.selectbox("Tipo de habitación", ["Sencilla", "Doble", "Familiar", "Suite"])
                n = c3.number_input("Habitaciones", 1, 10, 1)
                if st.form_submit_button("Agregar al carrito"):
                    agregar({"tipo": "hotel", "hotel_id": h["id"], "tipo_habitacion": tipo, "fecha_entrada": entrada.isoformat(),
                             "noches": int(noches), "cantidad": int(n)},
                            f"{h['nombre']} · {n} hab. {tipo} · {noches} noches desde {entrada}")

    with t_tours:
        ciu = ciudad_select("Ciudad", "t_c")
        ok, tours = api("GET", "/tours/", params={"ciudad": ciu} if ciu else {})
        if mostrar(ok, tours) and tours:
            for t in tours:
                with st.expander(f"{t['nombre']} — {t['ciudad']['nombre']} · {t['duracion_horas']} h"):
                    st.write(t["descripcion"])
                    st.caption(f"Incluye: {', '.join(t['incluye'])} · Punto de encuentro: {t['punto_encuentro']['nombre']}")
                    st.dataframe(pd.DataFrame([{"Salida": fecha(s["fecha"]), "Precio": pesos(s["precio"]),
                                                "Cupos": s["cupos_disponibles"]} for s in t["salidas"]]),
                                 hide_index=True, width="stretch")
                    with st.form(f"f_tour_{t['id']}"):
                        c1, c2 = st.columns(2)
                        s = c1.selectbox("Salida", t["salidas"], format_func=lambda s: f"{fecha(s['fecha'])} · {s['cupos_disponibles']} cupos")
                        n = c2.number_input("Cupos", 1, 20, 1)
                        if st.form_submit_button("Agregar al carrito"):
                            agregar({"tipo": "tour", "tour_id": t["id"], "salida_id": s["salida_id"], "cantidad": int(n)},
                                    f"Tour {t['nombre']} · {fecha(s['fecha'])} × {n}")

    with t_paquetes:
        personas = st.number_input("Personas", 1, 20, 2, key="p_n")
        ok, paquetes = api("GET", "/paquetes/", params={"personas": personas})
        if mostrar(ok, paquetes) and paquetes:
            for p in paquetes:
                cot = p["cotizacion"]
                icono = "✅" if cot["disponible"] else "⛔"
                with st.expander(f"{icono} {p['nombre']} — {p['descuento_pct']}% de descuento"):
                    for c in p["componentes"]:
                        st.write("• " + c["descripcion"])
                    st.caption(f"Vigente del {fecha(p['vigencia']['desde'], False)} al {fecha(p['vigencia']['hasta'], False)}")
                    if cot["disponible"]:
                        st.metric(f"Precio para {personas} persona(s)", pesos(cot["precio"]),
                                  delta=f"-{pesos(cot['suma_componentes'] - cot['precio'])}", delta_color="inverse")
                        if st.button("Agregar al carrito", key=f"pk_{p['codigo']}"):
                            agregar({"tipo": "paquete", "paquete_codigo": p["codigo"], "cantidad": int(personas)},
                                    f"Paquete {p['nombre']} · {personas} persona(s)")
                    else:
                        st.warning(cot["motivo"])

    st.divider()
    st.subheader("🛒 Reserva en preparación")
    if not st.session_state.carrito:
        st.info("Agregue vuelos, hoteles, tours o un paquete desde las pestañas de arriba.")
    else:
        for i, c in enumerate(st.session_state.carrito):
            c1, c2 = st.columns([8, 1])
            c1.write(f"{i + 1}. {c['etiqueta']}")
            if c2.button("Quitar", key=f"q_{i}"):
                st.session_state.carrito.pop(i)
                st.rerun()
        clientes = cargar("/clientes/")
        cliente = st.selectbox("Cliente", clientes, format_func=lambda c: f"{c['nombre']} — {c['documento']}")
        st.write("Pasajeros")
        base = pd.DataFrame([{"nombre": cliente["nombre"] if cliente else "", "documento": cliente["documento"] if cliente else "",
                              "fecha_nacimiento": date(1990, 1, 1)}])
        pax = st.data_editor(base, num_rows="dynamic", width="stretch", key="pax",
                             column_config={"fecha_nacimiento": st.column_config.DateColumn("fecha_nacimiento")})
        c1, c2 = st.columns(2)
        if c1.button("Crear reserva", type="primary"):
            pasajeros = [{"nombre": r["nombre"], "documento": str(r["documento"]),
                          "fecha_nacimiento": pd.to_datetime(r["fecha_nacimiento"]).date().isoformat()}
                         for _, r in pax.dropna(how="all").iterrows() if r["nombre"]]
            ok, r = api("POST", "/reservas/", json={"cliente_documento": cliente["documento"], "asesor_codigo": asesor["codigo"],
                                                    "usuario": USUARIO, "items": [c["item"] for c in st.session_state.carrito],
                                                    "pasajeros": pasajeros})
            if mostrar(ok, r, f"Reserva {r['codigo'] if ok else ''} creada: total {pesos(r['total']) if ok else ''} · estado Pendiente"):
                st.session_state.carrito = []
                st.session_state.reserva_sel = r["codigo"]
                st.cache_data.clear()
        if c2.button("Vaciar carrito"):
            st.session_state.carrito = []
            st.rerun()

elif modulo == "Reservas":
    st.header("Reservas")
    c1, c2 = st.columns([1, 2])
    estado = c1.selectbox("Estado", ["", "Pendiente", "Pagada", "Cancelada"], format_func=lambda e: e or "Todos")
    ok, lista = api("GET", "/reservas/", params={"estado": estado} if estado else {})
    if mostrar(ok, lista) and lista:
        st.dataframe(pd.DataFrame([{"Código": r["codigo"], "Fecha": fecha(r["fecha_creacion"]), "Cliente": r["cliente"]["nombre"],
                                    "Asesor": r["asesor"]["nombre"], "Estado": r["estado"], "Total": pesos(r["total"]),
                                    "Pagado": pesos(r["total_pagado"]), "Saldo": pesos(r.get("saldo", 0))} for r in lista]),
                     hide_index=True, width="stretch", height=260)
    codigos = [r["codigo"] for r in lista] if ok else []
    defecto = st.session_state.get("reserva_sel")
    codigo = c2.text_input("Código de la reserva", value=defecto or (codigos[0] if codigos else ""))
    if codigo:
        ok, r = api("GET", f"/reservas/{codigo.strip()}")
        if mostrar(ok, r):
            st.subheader(f"{r['codigo']} · {r['estado']}")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total", pesos(r["total"]))
            m2.metric("Pagado", pesos(r["total_pagado"]))
            m3.metric("Saldo", pesos(r["total"] - r["total_pagado"]))
            m4.metric("Pasajeros", len(r["pasajeros"]))
            st.caption(f"Cliente: {r['cliente']['nombre']} ({r['cliente']['documento']}) · Asesor: {r['asesor']['nombre']} · "
                       f"Creada: {fecha(r['fecha_creacion'])}")
            st.write("**Ítems** (precio vigente al reservar)")
            st.dataframe(pd.DataFrame([{"Tipo": i["tipo"], "Descripción": i["descripcion"], "Cantidad": i["cantidad"],
                                        "Precio unitario": pesos(i["precio_unitario"]), "Subtotal": pesos(i["subtotal"])}
                                       for i in r["items"]]), hide_index=True, width="stretch")
            for i in r["items"]:
                if i["tipo"] == "paquete":
                    with st.expander(f"Componentes de {i['paquete_nombre']} (suma {pesos(i['suma_componentes'])} − {i['descuento_pct']}%)"):
                        st.dataframe(pd.DataFrame([{"Descripción": c["descripcion"], "Cantidad": c["cantidad"],
                                                    "Subtotal": pesos(c["subtotal"])} for c in i["componentes"]]), hide_index=True)
            c1, c2, c3 = st.columns(3)
            c1.write("**Pasajeros**")
            c1.dataframe(pd.DataFrame(r["pasajeros"]).assign(fecha_nacimiento=lambda d: d["fecha_nacimiento"].str[:10]), hide_index=True)
            c2.write("**Pagos**")
            c2.dataframe(pd.DataFrame([{"Fecha": fecha(p["fecha"]), "Valor": pesos(p["valor"]), "Medio": p["medio"],
                                        "Usuario": p["usuario"]} for p in r["pagos"]]), hide_index=True)
            c3.write("**Historial de estados**")
            c3.dataframe(pd.DataFrame([{"Fecha": fecha(h["fecha"]), "De": h["estado_anterior"] or "—", "A": h["estado_nuevo"],
                                        "Usuario": h["usuario"]} for h in r["historial"]]), hide_index=True)

            st.divider()
            c1, c2 = st.columns(2)
            with c1.form("f_pago"):
                st.write("**Registrar pago**")
                valor = st.number_input("Valor", min_value=0.0, value=float(max(r["total"] - r["total_pagado"], 0)), step=10000.0)
                medio = st.selectbox("Medio de pago", ["Tarjeta de crédito", "Tarjeta débito", "PSE", "Transferencia", "Efectivo"])
                if st.form_submit_button("Registrar pago"):
                    ok, res = api("POST", f"/reservas/{r['codigo']}/pagos", json={"valor": valor, "medio": medio, "usuario": USUARIO})
                    if mostrar(ok, res, f"Pago registrado. Estado: {res.get('estado') if ok else ''}"):
                        st.session_state.reserva_sel = r["codigo"]
                        st.rerun()
            with c2.form("f_cancelar"):
                st.write("**Cancelar reserva** (devuelve sillas, habitaciones y cupos)")
                motivo = st.text_input("Motivo", "Solicitud del cliente")
                if st.form_submit_button("Cancelar reserva", type="primary"):
                    ok, res = api("POST", f"/reservas/{r['codigo']}/cancelar", json={"usuario": USUARIO, "motivo": motivo})
                    if mostrar(ok, res, "Reserva cancelada; inventario devuelto."):
                        st.session_state.reserva_sel = r["codigo"]
                        st.rerun()

elif modulo == "Catálogo y clientes":
    st.header("Catálogo y clientes")
    tc, tv, th, tt, tp = st.tabs(["Clientes", "Vuelo", "Hotel", "Tour", "Paquete"])

    with tc:
        with st.form("f_cliente"):
            c1, c2 = st.columns(2)
            doc = c1.text_input("Documento")
            nom = c2.text_input("Nombre")
            correo = c1.text_input("Correo")
            tel = c2.text_input("Teléfono")
            favs = st.multiselect("Destinos favoritos (opcional)", IATAS)
            pres = c1.number_input("Presupuesto (opcional)", 0, 100_000_000, 0, step=100_000)
            ninos = c2.checkbox("Viaja con niños")
            if st.form_submit_button("Registrar cliente"):
                datos = {"documento": doc, "nombre": nom, "correo": correo, "telefono": tel}
                if favs or pres or ninos:
                    datos["preferencias"] = {"destinos_favoritos": favs, "presupuesto": pres or None, "viaja_con_ninos": ninos}
                ok, res = api("POST", "/clientes/", json=datos)
                if mostrar(ok, res, "Cliente registrado"):
                    st.cache_data.clear()
        ok, cl = api("GET", "/clientes/")
        if ok:
            st.dataframe(pd.DataFrame(cl)[["documento", "nombre", "correo", "telefono"]], hide_index=True, width="stretch")

    with tv:
        with st.form("f_nuevo_vuelo"):
            c1, c2, c3 = st.columns(3)
            cod = c1.text_input("Código", "BV1234")
            aer = c2.text_input("Aerolínea", "Avianca")
            o = c1.selectbox("Origen", IATAS, key="nv_o")
            d = c2.selectbox("Destino", IATAS, index=1 if len(IATAS) > 1 else 0, key="nv_d")
            fs = c3.date_input("Fecha de salida", date.today() + timedelta(days=10))
            hs = c3.time_input("Hora de salida", datetime.strptime("08:00", "%H:%M").time())
            dur = c3.number_input("Duración (minutos)", 30, 600, 90)
            st.write("Tarifas (deje en 0 las sillas de una tarifa que no se ofrezca)")
            tarifas = []
            for tipo, precio, eq in [("Básica", 250000, "Artículo personal"), ("Clásica", 340000, "Maleta 23 kg"),
                                     ("Flexible", 450000, "Maleta 23 kg + cambios")]:
                a, b, c = st.columns(3)
                p_ = a.number_input(f"Precio {tipo}", 0, 10_000_000, precio, step=10000)
                s_ = b.number_input(f"Sillas {tipo}", 0, 300, 20)
                e_ = c.text_input(f"Equipaje {tipo}", eq)
                if s_ > 0:
                    tarifas.append({"tipo": tipo, "precio": p_, "equipaje": e_, "sillas": s_})
            if st.form_submit_button("Registrar vuelo"):
                salida = datetime.combine(fs, hs)
                ok, res = api("POST", "/vuelos/", json={"codigo": cod.upper(), "aerolinea": aer, "origen": o, "destino": d,
                                                        "salida": salida.isoformat(),
                                                        "llegada": (salida + timedelta(minutes=dur)).isoformat(), "tarifas": tarifas})
                mostrar(ok, res, f"Vuelo {cod} registrado")

    with th:
        with st.form("f_nuevo_hotel"):
            c1, c2, c3 = st.columns(3)
            nom = c1.text_input("Nombre")
            ciu = c2.selectbox("Ciudad", IATAS, key="nh_c")
            cat = c3.slider("Categoría (estrellas)", 1, 5, 4)
            dire = c1.text_input("Dirección")
            lat = c2.number_input("Latitud", -90.0, 90.0, 10.42, format="%.4f")
            lon = c3.number_input("Longitud", -180.0, 180.0, -75.55, format="%.4f")
            serv = st.multiselect("Servicios", ["piscina", "wifi", "desayuno incluido", "spa", "gimnasio", "frente al mar", "parqueadero"])
            tipos = []
            for tipo, cap, precio in [("Sencilla", 1, 200000), ("Doble", 2, 300000), ("Familiar", 4, 450000), ("Suite", 3, 700000)]:
                a, b, c = st.columns(3)
                n_ = a.number_input(f"Habitaciones {tipo}", 0, 500, 0)
                p_ = b.number_input(f"Precio/noche {tipo}", 0, 20_000_000, precio, step=10000)
                k_ = c.number_input(f"Capacidad {tipo}", 1, 10, cap)
                if n_ > 0:
                    tipos.append({"tipo": tipo, "capacidad": k_, "precio_noche": p_, "total_habitaciones": n_})
            dias = st.number_input("Noches a abrir en el calendario desde hoy", 1, 365, 60)
            if st.form_submit_button("Registrar hotel"):
                ok, res = api("POST", "/hoteles/", json={"nombre": nom, "ciudad": ciu, "direccion": dire, "categoria": cat,
                                                         "servicios": serv, "latitud": lat, "longitud": lon,
                                                         "tipos_habitacion": tipos, "dias_calendario": dias})
                mostrar(ok, res, f"Hotel registrado con calendario de {dias} noches")

    with tt:
        with st.form("f_nuevo_tour"):
            c1, c2, c3 = st.columns(3)
            nom = c1.text_input("Nombre del tour")
            ciu = c2.selectbox("Ciudad", IATAS, key="nt_c")
            dur = c3.number_input("Duración (horas)", 0.5, 72.0, 4.0)
            desc = st.text_area("Descripción")
            inc = st.text_input("Qué incluye (separado por comas)", "guía, transporte")
            pe = c1.text_input("Punto de encuentro")
            lat = c2.number_input("Latitud", -90.0, 90.0, 10.42, format="%.4f", key="nt_lat")
            lon = c3.number_input("Longitud", -180.0, 180.0, -75.55, format="%.4f", key="nt_lon")
            st.write("Salidas programadas")
            sal = st.data_editor(pd.DataFrame([{"fecha": (datetime.now() + timedelta(days=i * 3 + 2)).replace(hour=9, minute=0, second=0, microsecond=0),
                                                "precio": 120000, "cupos": 15} for i in range(3)]),
                                 num_rows="dynamic", key="nt_sal",
                                 column_config={"fecha": st.column_config.DatetimeColumn("fecha")})
            if st.form_submit_button("Registrar tour"):
                salidas = [{"fecha": pd.to_datetime(r["fecha"]).isoformat(), "precio": float(r["precio"]), "cupos": int(r["cupos"])}
                           for _, r in sal.dropna().iterrows()]
                ok, res = api("POST", "/tours/", json={"nombre": nom, "ciudad": ciu, "descripcion": desc, "duracion_horas": dur,
                                                       "incluye": [x.strip() for x in inc.split(",") if x.strip()],
                                                       "punto_encuentro": {"nombre": pe, "latitud": lat, "longitud": lon},
                                                       "salidas": salidas})
                mostrar(ok, res, "Tour registrado")

    with tp:
        st.caption("Un paquete combina vuelos, noches de hotel y tours; solo se vende si TODOS sus componentes tienen cupo.")
        vuelos_ok, vuelos = api("GET", "/vuelos/")
        hoteles_ok, hoteles = api("GET", "/hoteles/")
        tours_ok, tours = api("GET", "/tours/")
        if vuelos_ok and hoteles_ok and tours_ok:
            with st.form("f_nuevo_paquete"):
                c1, c2, c3 = st.columns(3)
                cod = c1.text_input("Código", "PKG-NUEVO")
                nom = c2.text_input("Nombre", "Escapada")
                des = c3.selectbox("Destino", IATAS, key="np_d")
                dcto = c1.number_input("Descuento %", 0.0, 100.0, 10.0)
                vd = c2.date_input("Vigente desde", date.today())
                vh = c3.date_input("Vigente hasta", date.today() + timedelta(days=30))
                fmt_v = lambda v: f"{v['codigo']} {v['origen']['iata']}→{v['destino']['iata']} {fecha(v['salida'])}"
                vi = st.selectbox("Vuelo de ida", vuelos, format_func=fmt_v)
                vr = st.selectbox("Vuelo de regreso", vuelos, format_func=fmt_v)
                tar = st.selectbox("Tarifa de los vuelos", ["Básica", "Clásica", "Flexible"])
                h = st.selectbox("Hotel", hoteles, format_func=lambda h: f"{h['nombre']} ({h['ciudad']['iata']})")
                a, b, c = st.columns(3)
                tipo_h = a.selectbox("Habitación", ["Doble", "Sencilla", "Familiar", "Suite"])
                fe = b.date_input("Entrada al hotel", date.today() + timedelta(days=10))
                no = c.number_input("Noches", 1, 30, 3)
                opciones_tour = [(t, s) for t in tours for s in t["salidas"]]
                ts = st.selectbox("Tour (salida)", opciones_tour, format_func=lambda x: f"{x[0]['nombre']} · {fecha(x[1]['fecha'])}")
                if st.form_submit_button("Registrar paquete"):
                    comps = [{"tipo": "vuelo", "vuelo_codigo": vi["codigo"], "tarifa": tar},
                             {"tipo": "hotel", "hotel_id": h["id"], "tipo_habitacion": tipo_h, "fecha_entrada": fe.isoformat(), "noches": no},
                             {"tipo": "tour", "tour_id": ts[0]["id"], "salida_id": ts[1]["salida_id"]},
                             {"tipo": "vuelo", "vuelo_codigo": vr["codigo"], "tarifa": tar}]
                    ok, res = api("POST", "/paquetes/", json={"codigo": cod, "nombre": nom, "destino": des, "descuento_pct": dcto,
                                                              "vigencia_desde": vd.isoformat(), "vigencia_hasta": vh.isoformat(),
                                                              "componentes": comps})
                    mostrar(ok, res, f"Paquete {cod} registrado")

else:
    st.header("Reportes (pipelines de agregación en MongoDB)")
    st.caption("Ningún reporte cuenta reservas canceladas.")

    st.subheader("B1. Ventas por mes")
    ok, b1 = api("GET", "/reportes/ventas-por-mes")
    if mostrar(ok, b1) and b1:
        df = pd.DataFrame(b1)
        fig = px.bar(df, x="periodo", y="total_vendido", text="reservas",
                     labels={"periodo": "Mes", "total_vendido": "Total vendido (COP)", "reservas": "Reservas"})
        fig.update_traces(texttemplate="%{text} reservas", textposition="outside")
        st.plotly_chart(fig, width="stretch")
        st.dataframe(df[["periodo", "reservas", "total_vendido", "total_recaudado", "ticket_promedio"]], hide_index=True)

    st.subheader("B2. Destinos más vendidos (top 5 por ingresos)")
    ok, b2 = api("GET", "/reportes/destinos-mas-vendidos")
    if mostrar(ok, b2) and b2:
        df = pd.DataFrame(b2)
        c1, c2 = st.columns([3, 2])
        c1.plotly_chart(px.bar(df, x="ingresos", y="ciudad", orientation="h", text="pasajeros",
                               labels={"ingresos": "Ingresos (COP)", "ciudad": "", "pasajeros": "Pasajeros"})
                        .update_traces(texttemplate="%{text} pasajeros").update_yaxes(autorange="reversed"),
                        width="stretch")
        c2.dataframe(df[["ciudad", "iata", "ingresos", "pasajeros", "reservas"]], hide_index=True)

    st.subheader("B3. Ocupación de vuelos")
    ok, b3 = api("GET", "/reportes/ocupacion-vuelos")
    if mostrar(ok, b3) and b3:
        df = pd.DataFrame(b3)
        df["salida"] = df["salida"].map(fecha)
        st.plotly_chart(px.bar(df, x="codigo", y="ocupacion_pct", hover_data=["ruta", "salida", "sillas_vendidas", "sillas_totales"],
                               labels={"codigo": "Vuelo", "ocupacion_pct": "Ocupación (%)"}), width="stretch")
        st.dataframe(df[["codigo", "aerolinea", "ruta", "salida", "sillas_totales", "sillas_vendidas", "ocupacion_pct"]],
                     hide_index=True, width="stretch")
