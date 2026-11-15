/* =====================================================================
   EMATEL · configuración común de Chart.js
   Requiere Chart.js cargado antes. Los colores salen de theme.css para que
   haya una sola fuente de verdad.
   ===================================================================== */
(() => {
  'use strict';
  if (!window.Chart) return;

  const css = (v, alt) => (getComputedStyle(document.documentElement).getPropertyValue(v) || alt).trim();
  const alfa = (hex, a) => {
    const h = hex.replace('#', '');
    return `rgba(${parseInt(h.slice(0, 2), 16)},${parseInt(h.slice(2, 4), 16)},${parseInt(h.slice(4, 6), 16)},${a})`;
  };

  const colores = {
    water: css('--water', '#0891b2'),
    gas: css('--gas', '#e2730b'),
    prev: css('--prev', '#94a3b8'),
    linea: css('--line-soft', '#eef1f5'),
    texto: css('--fg-muted', '#66748a'),
  };

  Chart.defaults.font.family = css('--font', 'sans-serif');
  Chart.defaults.font.size = 12;
  Chart.defaults.color = colores.texto;

  const MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
  const numero = new Intl.NumberFormat('es-CL', { maximumFractionDigits: 1 });

  function opciones() {
    return {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: { grid: { display: false }, border: { display: false }, ticks: { maxRotation: 0, autoSkipPadding: 6 } },
        y: {
          beginAtZero: true,
          border: { display: false },
          grid: { color: colores.linea },
          ticks: { maxTicksLimit: 5, callback: (v) => numero.format(v) },
        },
      },
      plugins: {
        legend: {
          position: 'bottom', align: 'start',
          labels: { usePointStyle: true, pointStyle: 'rectRounded', boxWidth: 8, boxHeight: 8, padding: 14 },
        },
        tooltip: {
          padding: 10,
          callbacks: {
            label: (c) => ` ${c.dataset.label}: ${c.parsed.y == null ? 'sin dato' : numero.format(c.parsed.y) + ' m³'}`,
          },
        },
      },
    };
  }

  /** Dataset de barras: año principal en color, comparación en gris. */
  function barras(etiqueta, datos, color, principal) {
    return {
      type: 'bar', label: etiqueta, data: datos,
      backgroundColor: principal ? color : alfa(colores.prev, 0.45),
      hoverBackgroundColor: principal ? color : colores.prev,
      borderRadius: 4, maxBarThickness: 22, categoryPercentage: 0.7, barPercentage: 0.9,
      order: principal ? 1 : 2,
    };
  }

  /** Dataset de línea: año principal sólido con relleno, comparación punteada. */
  function linea(etiqueta, datos, color, principal) {
    return {
      type: 'line', label: etiqueta, data: datos,
      borderColor: principal ? color : colores.prev,
      backgroundColor: principal ? alfa(color, 0.10) : 'transparent',
      fill: principal, borderWidth: principal ? 2.5 : 2, borderDash: principal ? [] : [5, 4],
      tension: 0.35, pointRadius: 0, pointHoverRadius: 4, spanGaps: false,
      order: principal ? 1 : 2,
    };
  }

  /** Corta la serie en el último mes transcurrido para no dibujar ceros futuros. */
  function recortar(serie, hastaMes) {
    if (hastaMes == null || hastaMes >= 12) return serie;
    return serie.map((v, i) => (i < hastaMes ? v : null));
  }

  const suma = (serie) => serie.reduce((t, v) => t + (v || 0), 0);

  window.EMATEL_GRAFICOS = { colores, MESES, numero, opciones, barras, linea, recortar, suma };
})();
