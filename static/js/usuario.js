/* =====================================================================
   EMATEL · panel del cliente (user_dashboard.html)
   ===================================================================== */
(() => {
  'use strict';
  const { postJSON, leerJSON } = window.EMATEL;

  /* ------------------------------ Gráficos ----------------------------- */
  (() => {
    const G = window.EMATEL_GRAFICOS;
    const series = leerJSON('series-consumo') || {};
    const anios = Object.keys(series).map(Number).sort((a, b) => b - a);
    if (!G || !anios.length) return;

    const selA = document.getElementById('anioA');
    const selB = document.getElementById('anioB');
    anios.forEach((a) => { selA.add(new Option(a, a)); selB.add(new Option(a, a)); });
    selA.value = anios[0];
    selB.value = anios[1] ?? anios[0];

    const gAgua = new Chart(document.getElementById('graficoAgua'), { type: 'bar', data: { labels: G.MESES, datasets: [] }, options: G.opciones() });
    const gGas = new Chart(document.getElementById('graficoGas'), { type: 'line', data: { labels: G.MESES, datasets: [] }, options: G.opciones() });
    const totalAgua = document.getElementById('totalAgua');
    const totalGas = document.getElementById('totalGas');

    function actualizar() {
      const a = Number(selA.value), b = Number(selB.value);
      const A = series[a], B = series[b];
      const mismo = a === b;

      gAgua.data.datasets = [G.barras(`Agua ${a}`, A.water, G.colores.water, true)];
      gGas.data.datasets = [G.linea(`Gas ${a}`, A.gas, G.colores.gas, true)];
      if (!mismo) {
        gAgua.data.datasets.push(G.barras(`Agua ${b}`, B.water, G.colores.water, false));
        gGas.data.datasets.push(G.linea(`Gas ${b}`, B.gas, G.colores.gas, false));
      }
      gAgua.update();
      gGas.update();

      totalAgua.textContent = `${G.numero.format(G.suma(A.water))} m³ en ${a}`;
      totalGas.textContent = `${G.numero.format(G.suma(A.gas))} m³ en ${a}`;
    }

    selA.addEventListener('change', actualizar);
    selB.addEventListener('change', actualizar);
    document.getElementById('intercambiarAnios').addEventListener('click', () => {
      [selA.value, selB.value] = [selB.value, selA.value];
      actualizar();
    });
    actualizar();
  })();

  /* ------------------------------ Reportes ----------------------------- */
  (() => {
    const caja = document.getElementById('reportes');
    if (!caja) return;

    const frecuencia = document.getElementById('rep-frecuencia');
    const formato = document.getElementById('rep-formato');
    const email = document.getElementById('rep-email');
    const estado = document.getElementById('rep-estado');
    const descargar = document.getElementById('rep-descargar');
    const enviar = document.getElementById('rep-enviar');
    let temporizador;

    const avisar = (texto, esError) => {
      estado.textContent = texto;
      estado.style.color = esError ? 'var(--danger)' : 'var(--ok)';
      estado.classList.remove('hidden');
      clearTimeout(temporizador);
      temporizador = setTimeout(() => estado.classList.add('hidden'), 3000);
    };

    const actualizarDescarga = () => {
      const url = new URL(descargar.href, location.origin);
      url.searchParams.set('format', formato.value);
      descargar.href = url.pathname + url.search;
    };

    async function guardar() {
      try {
        const r = await postJSON(caja.dataset.urlGuardar, {
          report_frequency: frecuencia.value,
          report_format: formato.value,
          report_email: email.value,
        });
        avisar(r.ok ? 'Preferencias guardadas' : 'Revisa el email ingresado', !r.ok);
      } catch {
        avisar('No se pudieron guardar las preferencias', true);
      }
    }

    frecuencia.addEventListener('change', guardar);
    formato.addEventListener('change', () => { actualizarDescarga(); guardar(); });
    email.addEventListener('change', guardar);

    enviar.addEventListener('click', async () => {
      const original = enviar.innerHTML;
      enviar.disabled = true;
      enviar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enviando…';
      try {
        const r = await postJSON(caja.dataset.urlEnviar, {
          year: Number(caja.dataset.anio) || new Date().getFullYear(),
          format: formato.value,
          to: email.value,
        });
        avisar(r.ok ? `Reporte enviado a ${email.value}` : `No se pudo enviar: ${r.data.error || 'error'}`, !r.ok);
      } catch {
        avisar('Error de conexión', true);
      } finally {
        enviar.disabled = false;
        enviar.innerHTML = original;
      }
    });
  })();
})();
