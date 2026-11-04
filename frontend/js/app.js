const $ = (id) => document.getElementById(id);
const MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
const dinero = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });

let clientes = [];
let productos = [];
let ventas = [];

function avisar(texto, tipo = "exito") {
  const caja = $("mensaje");
  caja.textContent = texto;
  caja.className = `mensaje ${tipo}`;
  clearTimeout(avisar.temporizador);
  avisar.temporizador = setTimeout(() => caja.classList.add("oculto"), 5000);
}

async function intentar(funcion) {
  try {
    await funcion();
  } catch (e) {
    const pista = e.estado === 401 ? " Inicie sesión en Configuración." : "";
    avisar(e.message + pista, "error");
    console.error(e);
  }
}

async function deLaboratorio(numero, funcion) {
  try {
    return await funcion();
  } catch (e) {
    if (e.estado === 404) {
      throw new Error(`Esta función se activa en el Laboratorio ${numero}.`);
    }
    throw e;
  }
}

function fila(celdas, acciones = []) {
  const tr = document.createElement("tr");
  for (const valor of celdas) {
    const td = document.createElement("td");
    if (valor instanceof Node) td.appendChild(valor);
    else td.textContent = valor ?? "";
    tr.appendChild(td);
  }
  if (acciones.length) {
    const td = document.createElement("td");
    for (const a of acciones) {
      const b = document.createElement("button");
      b.textContent = a.texto;
      if (a.clase) b.className = a.clase;
      b.addEventListener("click", a.alHacerClic);
      td.appendChild(b);
    }
    tr.appendChild(td);
  }
  return tr;
}

function llenarSelect(select, opciones) {
  select.replaceChildren();
  for (const o of opciones) select.add(new Option(o.texto, o.valor));
}

function mostrarSeccion(id) {
  document.querySelectorAll(".seccion").forEach(s => s.classList.toggle("visible", s.id === id));
  document.querySelectorAll(".menu button").forEach(b => b.classList.toggle("activo", b.dataset.seccion === id));
  if (id === "panel") intentar(cargarPanel);
  if (id === "clientes") intentar(cargarClientes);
  if (id === "productos") intentar(cargarProductos);
  if (id === "ventas" || id === "ia") intentar(cargarVentas);
  if (id === "notificaciones") intentar(cargarNotificaciones);
}

document.querySelectorAll(".menu button").forEach(b => b.addEventListener("click", () => mostrarSeccion(b.dataset.seccion)));

async function verificarConexion() {
  const etiqueta = $("estado-conexion");
  try {
    const salud = await Api.get("/health");
    etiqueta.textContent = "conectado";
    etiqueta.className = "estado conectado";
    return salud.servicios || {};
  } catch (e) {
    etiqueta.textContent = "sin conexión";
    etiqueta.className = "estado error";
    throw e;
  }
}

async function cargarClientes() {
  clientes = await Api.get("/api/clientes");
  const cuerpo = $("tabla-clientes");
  cuerpo.replaceChildren(...clientes.map(c => fila([c.id, c.nombre, c.correo], [
    { texto: "Editar", alHacerClic: () => editarCliente(c) },
    { texto: "Eliminar", clase: "peligro", alHacerClic: () => eliminarCliente(c.id) }
  ])));
}

function editarCliente(c) {
  $("cliente-id").value = c.id;
  $("cliente-nombre").value = c.nombre;
  $("cliente-correo").value = c.correo;
}

async function eliminarCliente(id) {
  if (!confirm(`¿Eliminar el cliente ${id}?`)) return;
  await intentar(async () => {
    await Api.borrar(`/api/clientes/${id}`);
    avisar("Cliente eliminado");
    await cargarClientes();
  });
}

$("form-cliente").addEventListener("submit", (evento) => {
  evento.preventDefault();
  intentar(async () => {
    const id = $("cliente-id").value;
    const datos = { nombre: $("cliente-nombre").value, correo: $("cliente-correo").value };
    if (id) await Api.put(`/api/clientes/${id}`, datos);
    else await Api.post("/api/clientes", datos);
    avisar(id ? "Cliente actualizado" : "Cliente creado");
    evento.target.reset();
    $("cliente-id").value = "";
    await cargarClientes();
  });
});
$("form-cliente").addEventListener("reset", () => { $("cliente-id").value = ""; });

async function cargarProductos(filtros = "") {
  productos = await Api.get("/api/productos" + filtros);
  const cuerpo = $("tabla-productos");
  cuerpo.replaceChildren(...productos.map(p => fila([p.id, p.nombre, dinero.format(p.precio), p.categoria, celdaImagen(p)], [
    { texto: "Editar", alHacerClic: () => editarProducto(p) },
    { texto: "Eliminar", clase: "peligro", alHacerClic: () => eliminarProducto(p.id) }
  ])));
  const opciones = productos.map(p => ({ valor: p.id, texto: `${p.id} ${p.nombre}` }));
  llenarSelect($("imagen-producto"), opciones);
}

function celdaImagen(p) {
  if (!p.imagen_key) return "";
  const img = document.createElement("img");
  img.alt = p.nombre;
  Api.get(`/api/imagenes/${p.id}`).then(r => { img.src = r.url; }).catch(() => {});
  return img;
}

function editarProducto(p) {
  $("producto-id").value = p.id;
  $("producto-nombre").value = p.nombre;
  $("producto-precio").value = p.precio;
  $("producto-categoria").value = p.categoria;
}

async function eliminarProducto(id) {
  if (!confirm(`¿Eliminar el producto ${id}?`)) return;
  await intentar(async () => {
    await Api.borrar(`/api/productos/${id}`);
    avisar("Producto eliminado");
    await cargarProductos();
  });
}

$("form-producto").addEventListener("submit", (evento) => {
  evento.preventDefault();
  intentar(async () => {
    const id = $("producto-id").value;
    const datos = {
      nombre: $("producto-nombre").value,
      precio: Number($("producto-precio").value),
      categoria: $("producto-categoria").value || "general"
    };
    if (id) await Api.put(`/api/productos/${id}`, datos);
    else await Api.post("/api/productos", datos);
    avisar(id ? "Producto actualizado" : "Producto creado");
    evento.target.reset();
    $("producto-id").value = "";
    await cargarProductos();
  });
});
$("form-producto").addEventListener("reset", () => { $("producto-id").value = ""; });

$("form-filtros").addEventListener("submit", (evento) => {
  evento.preventDefault();
  const params = new URLSearchParams();
  if ($("filtro-categoria").value) params.set("categoria", $("filtro-categoria").value);
  if ($("filtro-precio").value) params.set("precio_max", $("filtro-precio").value);
  const texto = params.toString();
  intentar(() => cargarProductos(texto ? `?${texto}` : ""));
});

$("form-imagen").addEventListener("submit", (evento) => {
  evento.preventDefault();
  intentar(async () => {
    const datos = new FormData();
    datos.append("producto_id", $("imagen-producto").value);
    datos.append("archivo", $("imagen-archivo").files[0]);
    await deLaboratorio(4, () => Api.post("/api/imagenes", datos));
    avisar("Imagen subida");
    evento.target.reset();
    await cargarProductos();
  });
});

async function cargarVentas() {
  [clientes, productos, ventas] = await Promise.all([
    Api.get("/api/clientes"), Api.get("/api/productos"), Api.get("/api/ventas")
  ]);
  const nomCliente = new Map(clientes.map(c => [c.id, c.nombre]));
  const nomProducto = new Map(productos.map(p => [p.id, p.nombre]));
  const recientes = [...ventas].reverse().slice(0, 100);

  $("tabla-ventas").replaceChildren(...recientes.map(v => fila(
    [v.id, v.fecha, nomCliente.get(v.cliente_id) ?? v.cliente_id, nomProducto.get(v.producto_id) ?? v.producto_id, v.cantidad, dinero.format(v.total)],
    [{ texto: "Eliminar", clase: "peligro", alHacerClic: () => eliminarVenta(v.id) }]
  )));

  llenarSelect($("venta-cliente"), clientes.map(c => ({ valor: c.id, texto: c.nombre })));
  const opcionesProducto = productos.map(p => ({ valor: p.id, texto: p.nombre }));
  llenarSelect($("venta-producto"), opcionesProducto);
  llenarSelect($("pred-producto"), opcionesProducto);
  ponerPrecioPrediccion();

  // Función 10 puntos: Buscador en tiempo real
  $("buscar-venta").oninput = (evento) => {
    const texto = evento.target.value.toLowerCase();
    const ventasFiltradas = ventas.filter(v => {
      const nombreCliente = nomCliente.get(v.cliente_id) ?? String(v.cliente_id);
      return nombreCliente.toLowerCase().includes(texto);
    });
    const recientesFiltradas = [...ventasFiltradas].reverse().slice(0, 100);
    $("tabla-ventas").replaceChildren(...recientesFiltradas.map(v => fila(
      [v.id, v.fecha, nomCliente.get(v.cliente_id) ?? v.cliente_id, nomProducto.get(v.producto_id) ?? v.producto_id, v.cantidad, dinero.format(v.total)],
      [{ texto: "Eliminar", clase: "peligro", alHacerClic: () => eliminarVenta(v.id) }]
    )));
  };
}

async function eliminarVenta(id) {
  if (!confirm(`¿Eliminar la venta ${id}?`)) return;
  await intentar(async () => {
    await Api.borrar(`/api/ventas/${id}`);
    avisar("Venta eliminada");
    await cargarVentas();
  });
}

$("form-venta").addEventListener("submit", (evento) => {
  evento.preventDefault();
  intentar(async () => {
    const datos = {
      cliente_id: Number($("venta-cliente").value),
      producto_id: Number($("venta-producto").value),
      cantidad: Number($("venta-cantidad").value),
    };
    if ($("venta-fecha").value) datos.fecha = $("venta-fecha").value;
    const venta = await Api.post("/api/ventas", datos);
    avisar(`Venta ${venta.id} registrada: ${dinero.format(venta.total)}`);
    await cargarVentas();
  });
});

function ponerPrecioPrediccion() {
  const p = productos.find(x => x.id === Number($("pred-producto").value));
  if (p) $("pred-precio").value = p.precio;
}

$("pred-producto").addEventListener("change", ponerPrecioPrediccion);
$("btn-entrenar").addEventListener("click", () => intentar(async () => {
  $("resultado-entrenamiento").textContent = "Entrenando...";
  const r = await Api.post("/api/ia/train");
  $("resultado-entrenamiento").textContent = `Modelo entrenado con ${r.ventas} ventas. MAE=${r.mae}, R2=${r.r2}`;
}));

function datosPrediccion() {
  return {
    producto_id: Number($("pred-producto").value),
    mes: Number($("pred-mes").value),
    precio: Number($("pred-precio").value),
  };
}

$("form-prediccion").addEventListener("submit", (evento) => {
  evento.preventDefault();
  intentar(async () => {
    const params = new URLSearchParams(datosPrediccion());
    const r = await Api.get(`/api/ia/predict?${params}`);
    $("resultado-prediccion").textContent = `Se estiman ${r.cantidad_estimada} unidades en ${MESES[r.mes - 1]}.`;
  });
});

$("btn-pred-async").addEventListener("click", () => intentar(async () => {
  const solicitud = await deLaboratorio(3, () => Api.post("/api/ia/solicitudes", datosPrediccion()));
  $("resultado-prediccion").textContent = `Solicitud ${solicitud.id}: pendiente...`;
  for (let intento = 0; intento < 30; intento++) {
    await new Promise(listo => setTimeout(listo, 1000));
    const r = await Api.get(`/api/ia/solicitudes/${solicitud.id}`);
    if (r.estado !== "pendiente") {
      $("resultado-prediccion").textContent = r.estado === "listo" ? `Resultado en cola: ${r.cantidad_estimada} unidades.` : `La solicitud terminó con estado: ${r.estado}`;
      return;
    }
  }
  $("resultado-prediccion").textContent = "Sin respuesta después de 30 s.";
}));

async function cargarPanel() {
  const servicios = await verificarConexion();
  $("lista-servicios").replaceChildren(...Object.entries(servicios).map(([n, ok]) => {
    const li = document.createElement("li");
    li.textContent = `${n}: ${ok ? "en línea" : "sin respuesta"}`;
    li.className = ok ? "ok" : "caido";
    return li;
  }));
  await cargarVentas();
  const ingresos = ventas.reduce((suma, v) => suma + v.total, 0);
  $("kpi-clientes").textContent = clientes.length;
  $("kpi-productos").textContent = productos.length;
  $("kpi-ventas").textContent = ventas.length;
  $("kpi-ingresos").textContent = dinero.format(ingresos);
  
  // Función 10 puntos: Ticket Promedio
  const ticketPromedio = ventas.length > 0 ? ingresos / ventas.length : 0;
  $("kpi-ticket").textContent = dinero.format(ticketPromedio);

  const porMes = new Array(12).fill(0);
  for (const v of ventas) porMes[Number(v.fecha.slice(5, 7)) - 1] += v.total;
  dibujarBarras($("grafica-meses"), MESES, porMes);

  const resumen = new Map();
  for (const v of ventas) {
    const r = resumen.get(v.producto_id) || { unidades: 0, ingresos: 0 };
    r.unidades += v.cantidad;
    r.ingresos += v.total;
    resumen.set(v.producto_id, r);
  }
  const nombre = new Map(productos.map(p => [p.id, p.nombre]));
  const top = [...resumen.entries()].sort((a, b) => b[1].unidades - a[1].unidades).slice(0, 5);
  $("tabla-top").replaceChildren(...top.map(([id, r]) => fila([nombre.get(id) ?? id, r.unidades, dinero.format(r.ingresos)])));
}

$("btn-actualizar-panel").addEventListener("click", () => intentar(cargarPanel));

function dibujarBarras(canvas, etiquetas, valores) {
  const ctx = canvas.getContext("2d");
  const ancho = canvas.width, alto = canvas.height;
  const margen = { izq: 60, abajo: 30, arriba: 15 };
  const maximo = Math.max(...valores, 1);
  const altoUtil = alto - margen.abajo - margen.arriba;
  const anchoBarra = (ancho - margen.izq) / valores.length;
  
  ctx.clearRect(0, 0, ancho, alto);
  ctx.font = "12px system-ui";
  ctx.fillStyle = "#52606d";
  for (const fraccion of [0, 0.5, 1]) {
    const y = margen.arriba + altoUtil * (1 - fraccion);
    ctx.fillText(Math.round(maximo * fraccion).toLocaleString("es-MX"), 2, y + 4);
    ctx.fillRect(margen.izq, y, ancho - margen.izq, 1);
  }
  valores.forEach((valor, i) => {
    const h = altoUtil * (valor / maximo);
    const x = margen.izq + i * anchoBarra + 4;
    ctx.fillStyle = "#204a87";
    ctx.fillRect(x, margen.arriba + altoUtil - h, anchoBarra - 8, h);
    ctx.fillStyle = "#1f2933";
    ctx.fillText(etiquetas[i], x, alto - 10);
  });
}

async function cargarNotificaciones() {
  const lista = await deLaboratorio(3, () => Api.get("/api/notificaciones?limite=20"));
  $("lista-notificaciones").replaceChildren(...lista.map(n => {
    const li = document.createElement("li");
    li.textContent = `[${n.evento}] ${n.mensaje}`;
    return li;
  }));
}

$("btn-notif").addEventListener("click", () => intentar(cargarNotificaciones));
setInterval(() => {
  if ($("auto-notif").checked) {
    intentar(cargarNotificaciones).then(() => {
      if ($("mensaje").classList.contains("error")) $("auto-notif").checked = false;
    });
  }
}, 3000);

function mostrarSesion() {
  const token = Api.token();
  if (!token) {
    $("info-sesion").textContent = "Sin sesión (normal antes del Laboratorio 6).";
    return;
  }
  try {
    const base64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const datos = JSON.parse(atob(base64));
    const expira = new Date(datos.exp * 1000).toLocaleTimeString("es-MX");
    $("info-sesion").textContent = `Sesión: ${datos.sub} (${(datos.roles || []).join(", ")}), expira a las ${expira}`;
  } catch (e) {
    $("info-sesion").textContent = "Hay un token guardado, pero no se pudo leer.";
  }
}

$("form-config").addEventListener("submit", (evento) => {
  evento.preventDefault();
  Api.fijarBase($("config-url").value);
  intentar(async () => {
    await verificarConexion();
    avisar(`Conectado a ${Api.base()}`);
  });
});

$("form-login").addEventListener("submit", (evento) => {
  evento.preventDefault();
  intentar(async () => {
    Api.fijarToken("");
    const r = await deLaboratorio(5, () => Api.post("/api/auth/login", { usuario: $("login-usuario").value, contrasena: $("login-contrasena").value }));
    Api.fijarToken(r.access_token);
    $("login-contrasena").value = "";
    mostrarSesion();
    avisar("Sesión iniciada");
  });
});

$("btn-salir").addEventListener("click", () => {
  Api.fijarToken("");
  mostrarSesion();
  avisar("Sesión cerrada");
});

$("config-url").value = Api.base();
mostrarSesion();
intentar(cargarPanel);