/* =====================================================================
   EMATEL · utilidades comunes a todas las páginas
   Expone el objeto global `EMATEL` con helpers pequeños y sin dependencias.
   ===================================================================== */
(() => {
  'use strict';

  /** Token CSRF leído de la cookie de Django. */
  function csrf() {
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    if (m) return decodeURIComponent(m[1]);
    const input = document.querySelector('[name=csrfmiddlewaretoken]');
    return input ? input.value : '';
  }

  /** POST con JSON. Devuelve { ok, status, data }. */
  async function postJSON(url, cuerpo) {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
      body: JSON.stringify(cuerpo),
    });
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok && data.ok !== false, status: res.status, data };
  }

  /** Lee un bloque generado con el filtro json_script de Django. */
  function leerJSON(id) {
    const el = document.getElementById(id);
    return el ? JSON.parse(el.textContent) : null;
  }

  /* ------------------------------ Modales ------------------------------ */
  function abrirModal(modal) {
    modal.classList.add('is-open');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }
  function cerrarModal(modal) {
    modal.classList.remove('is-open');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }
  document.querySelectorAll('.modal').forEach((modal) => {
    modal.querySelectorAll('[data-cerrar]').forEach((b) => b.addEventListener('click', () => cerrarModal(modal)));
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') document.querySelectorAll('.modal.is-open').forEach(cerrarModal);
  });

  /* ------------------------------ Pestañas -----------------------------
     <div class="tabs" data-tabs="x"><button class="tab" data-valor="2025">…
     <tbody data-tabla="x"><tr data-valor="2025">…
     Valor vacío = mostrar todo. */
  document.querySelectorAll('[data-tabs]').forEach((grupo) => {
    const filas = document.querySelectorAll(`[data-tabla="${grupo.dataset.tabs}"] [data-valor]`);
    const aplicar = (valor) => filas.forEach((f) => f.classList.toggle('hidden', !!valor && f.dataset.valor !== valor));
    grupo.querySelectorAll('.tab').forEach((tab) => {
      tab.addEventListener('click', () => {
        grupo.querySelectorAll('.tab').forEach((t) => t.classList.toggle('is-active', t === tab));
        aplicar(tab.dataset.valor);
      });
    });
    const activa = grupo.querySelector('.tab.is-active');
    if (activa) aplicar(activa.dataset.valor);
  });

  /* ------------------- Confirmación antes de enviar -------------------- */
  document.querySelectorAll('form[data-confirmar]').forEach((form) => {
    form.addEventListener('submit', (e) => {
      if (!window.confirm(form.dataset.confirmar)) e.preventDefault();
    });
  });

  window.EMATEL = { csrf, postJSON, leerJSON, abrirModal, cerrarModal };
})();
