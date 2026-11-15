/* =====================================================================
   EMATEL · página de consumo del administrador (admin/consumo.html)
   ===================================================================== */
(() => {
  'use strict';
  const { leerJSON } = window.EMATEL;

  /* ------------------------------ Gráficos ----------------------------- */
  (() => {
    const G = window.EMATEL_GRAFICOS;
    const datos = leerJSON('datos-graficos');
    if (!G || !datos) return;

    const { prev, now } = datos.years;
    const aguaAhora = G.recortar(datos.water.now, datos.hasta_mes);
    const gasAhora = G.recortar(datos.gas.now, datos.hasta_mes);

    new Chart(document.getElementById('graficoAgua'), {
      type: 'bar',
      data: {
        labels: datos.labels,
        datasets: [
          G.barras(`Agua ${now}`, aguaAhora, G.colores.water, true),
          G.barras(`Agua ${prev}`, datos.water.prev, G.colores.water, false),
        ],
      },
      options: G.opciones(),
    });

    new Chart(document.getElementById('graficoGas'), {
      type: 'line',
      data: {
        labels: datos.labels,
        datasets: [
          G.linea(`Gas ${now}`, gasAhora, G.colores.gas, true),
          G.linea(`Gas ${prev}`, datos.gas.prev, G.colores.gas, false),
        ],
      },
      options: G.opciones(),
    });

    document.getElementById('totalAgua').textContent = `${G.numero.format(G.suma(aguaAhora))} m³ en ${now}`;
    document.getElementById('totalGas').textContent = `${G.numero.format(G.suma(gasAhora))} m³ en ${now}`;
  })();

  /* -------- Cambiar de cliente recarga la sección de consumo -------- */
  const filtro = document.getElementById('filtroUsuario');
  if (filtro) filtro.addEventListener('change', () => filtro.form.submit());
})();
