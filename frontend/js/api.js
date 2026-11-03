/* Comunicación con el API Gateway de TiendaIA. */

function leerAjuste(clave, poromision) {
  try {
    return localStorage.getItem(clave) || poromision;
  } catch (e) {
    return poromision;
  }
}

function guardarAjuste(clave, valor) {
  try {
    if (valor) localStorage.setItem(clave, valor);
    else localStorage.removeItem(clave);
  } catch (e) { }
}

class ErrorApi extends Error {
  constructor(estado, detalle) {
    super(`HTTP ${estado}: ${detalle}`);
    this.estado = estado;
  }
}

const Api = {
  base() {
    return leerAjuste("tiendaia_api", "http://localhost:8080").replace(/\/+$/, "");
  },
  fijarBase(url) { guardarAjuste("tiendaia_api", url.trim()); },

  token() { return leerAjuste("tiendaia_token", ""); },
  fijarToken(t) { guardarAjuste("tiendaia_token", t); },

  async pedir(metodo, ruta, cuerpo) {
    const opciones = { method: metodo, headers: {} };
    
    if (cuerpo instanceof FormData) {
      opciones.body = cuerpo;
    } else if (cuerpo !== undefined) {
      opciones.headers["Content-Type"] = "application/json";
      opciones.body = JSON.stringify(cuerpo);
    }

    const token = this.token();
    if (token) opciones.headers["Authorization"] = `Bearer ${token}`;

    let resp;
    try {
      resp = await fetch(this.base() + ruta, opciones);
    } catch (e) {
      throw new ErrorApi(0, "no hubo respuesta del gateway (¿URL correcta? ¿CORS?)");
    }

    if (resp.status === 204) return null;

    const texto = await resp.text();
    let datos = null;
    try { datos = texto ? JSON.parse(texto) : null; } catch (e) { datos = texto; }

    if (!resp.ok) {
      let detalle = datos && datos.detail !== undefined ? datos.detail : texto;
      if (Array.isArray(detalle)) detalle = detalle.map(d => d.msg).join("; ");
      throw new ErrorApi(resp.status, detalle || resp.statusText);
    }
    
    return datos;
  },

  get(ruta) { return this.pedir("GET", ruta); },
  post(ruta, cuerpo) { return this.pedir("POST", ruta, cuerpo); },
  put(ruta, cuerpo) { return this.pedir("PUT", ruta, cuerpo); },
  borrar(ruta) { return this.pedir("DELETE", ruta); }
};