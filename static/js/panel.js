/* =====================================================================
   EMATEL · panel del administrador (admin/panel.html)
   Tarjetas expandibles: cada <details data-widget> recuerda si quedó
   abierta o cerrada. Los gráficos se dibujan la primera vez que se abre
   su tarjeta, así no se calculan en un contenedor oculto.
   ===================================================================== */
(() => {
  'use strict';
  const { leerJSON } = window.EMATEL;
  const CLAVE = 'ematel.panel.tarjetas';
  const tarjetas = Array.from(document.querySelectorAll('details[data-widget]'));

  /* --------------------------- Estado guardado -------------------------- */
  const leerEstado = () => {
    try { return JSON.parse(localStorage.getItem(CLAVE)) || {}; } catch { return {}; }
  };
  const guardarEstado = () => {
    const estado = {};
    tarjetas.forEach((t) => (estado[t.dataset.widget] = t.open));
    try { localStorage.setItem(CLAVE, JSON.stringify(estado)); } catch { /* sin almacenamiento */ }
  };

  const guardado = leerEstado();
  tarjetas.forEach((t) => {
    const id = t.dataset.widget;
    t.open = id in guardado ? !!guardado[id] : t.hasAttribute('data-abierto');
  });

  /* ------------------------------ Gráficos ----------------------------- */
  const dibujados = new Set();
  const graficos = {
    consumo() {
      const G = window.EMATEL_GRAFICOS;
      const d = leerJSON('datos-panel');
      if (!G || !d) return;
      const { prev, now } = d.years;
      new Chart(document.getElementById('panelAgua'), {
        type: 'bar',
        data: {
          labels: d.labels,
          datasets: [
            G.barras(`Agua ${now}`, G.recortar(d.actual.water, d.hasta_mes), G.colores.water, true),
            G.barras(`Agua ${prev}`, d.anterior.water, G.colores.water, false),
          ],
        },
        options: G.opciones(),
      });
      new Chart(document.getElementById('panelGas'), {
        type: 'line',
        data: {
          labels: d.labels,
          datasets: [
            G.linea(`Gas ${now}`, G.recortar(d.actual.gas, d.hasta_mes), G.colores.gas, true),
            G.linea(`Gas ${prev}`, d.anterior.gas, G.colores.gas, false),
          ],
        },
        options: G.opciones(),
      });
    },
  };
  const dibujar = (t) => {
    const id = t.dataset.widget;
    if (t.open && graficos[id] && !dibujados.has(id)) {
      dibujados.add(id);
      graficos[id]();
    }
  };

  tarjetas.forEach((t) => {
    dibujar(t);
    t.addEventListener('toggle', () => { dibujar(t); guardarEstado(); });
  });

  /* ---------------------- Expandir / contraer todo --------------------- */
  document.querySelectorAll('[data-widgets]').forEach((b) => {
    b.addEventListener('click', () => {
      const abrir = b.dataset.widgets === 'abrir';
      tarjetas.forEach((t) => (t.open = abrir));
    });
  });
})();
