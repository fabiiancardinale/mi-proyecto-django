/* =====================================================================
   EMATEL · listado de clientes (admin/clientes.html)
   Modales de detalle y edición.
   ===================================================================== */
(() => {
  'use strict';
  const { csrf, leerJSON, abrirModal, cerrarModal } = window.EMATEL;
  const fichas = leerJSON('fichas-usuarios') || {};

  /* --------------------------- Modal de detalle ------------------------ */
  const modalDetalle = document.getElementById('modalDetalle');
  let fichaAbierta = null;

  function mostrarDetalle(f) {
    fichaAbierta = f;
    const poner = (clave, valor) => {
      const el = modalDetalle.querySelector(`[data-d="${clave}"]`);
      if (el) el.textContent = valor || '—';
      return el;
    };

    poner('inicial', (f.username || '?').charAt(0).toUpperCase());
    poner('username', f.username);
    ['email', 'last_login', 'date_joined', 'location', 'external_id', 'manager_name',
     'address', 'last_maintenance', 'next_maintenance'].forEach((c) => poner(c, f[c]));
    poner('intervalo', f.maintenance_interval_months ? `${f.maintenance_interval_months} meses` : '');
    if (!f.last_login) poner('last_login', 'Nunca');

    const rol = poner('rol', f.role_label);
    rol.className = 'badge' + (f.role === 'admin' ? ' badge-dark' : '');
    const estado = poner('estado', f.is_active ? 'Activo' : 'Inactivo');
    estado.className = 'badge' + (f.is_active ? ' badge-ok' : '');

    const tel = poner('phone', f.phone);
    if (f.phone) tel.href = 'tel:' + f.phone.replace(/\s+/g, ''); else tel.removeAttribute('href');

    const link = poner('link', f.link || 'Sin link configurado');
    if (/^https?:\/\//i.test(f.link || '')) link.href = f.link; else link.removeAttribute('href');

    abrirModal(modalDetalle);
  }

  /* --------------------------- Modal de edición ------------------------ */
  const modalEditar = document.getElementById('modalEditar');
  const form = document.getElementById('formEditar');
  const boton = document.getElementById('btnGuardarEdicion');
  const errorGeneral = document.getElementById('e-error');
  const CAMPOS = ['username', 'email', 'role', 'location', 'external_id', 'manager_name', 'phone', 'address', 'link'];
  let urlEdicion = null;

  function limpiarErrores() {
    form.querySelectorAll('[data-error]').forEach((e) => (e.textContent = ''));
    form.querySelectorAll('.field').forEach((f) => f.classList.remove('has-error'));
    errorGeneral.classList.add('hidden');
  }

  function mostrarEdicion(f) {
    limpiarErrores();
    urlEdicion = f.edit_url;
    CAMPOS.forEach((c) => (form.elements[c].value = f[c] || ''));
    form.elements.is_active.value = f.is_active ? 'True' : '';
    abrirModal(modalEditar);
    setTimeout(() => form.elements.username.focus(), 50);
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    limpiarErrores();

    const datos = new FormData(form);
    // Vacío = inactivo: el BooleanField de Django interpreta la ausencia como False.
    if (!datos.get('is_active')) datos.delete('is_active');

    boton.disabled = true;
    const original = boton.innerHTML;
    boton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando…';

    try {
      const res = await fetch(urlEdicion, { method: 'POST', body: datos, headers: { 'X-CSRFToken': csrf() } });
      const payload = await res.json().catch(() => ({}));
      if (res.ok && payload.ok) { location.reload(); return; }

      const errores = payload.errores || {};
      let enCampo = false;
      Object.entries(errores).forEach(([campo, mensajes]) => {
        const destino = form.querySelector(`[data-error="${campo}"]`);
        if (!destino) return;
        destino.textContent = mensajes.join(' ');
        destino.closest('.field').classList.add('has-error');
        enCampo = true;
      });
      if (!enCampo) {
        errorGeneral.querySelector('div').textContent =
          Object.values(errores).flat().join(' ') || 'No se pudo guardar. Revisa los datos.';
        errorGeneral.classList.remove('hidden');
      }
    } catch {
      errorGeneral.querySelector('div').textContent = 'Error de conexión. Intenta de nuevo.';
      errorGeneral.classList.remove('hidden');
    } finally {
      boton.disabled = false;
      boton.innerHTML = original;
    }
  });

  /* ------------------------- Botones de la tabla ----------------------- */
  document.querySelectorAll('.js-ver').forEach((b) => b.addEventListener('click', () => mostrarDetalle(fichas[b.dataset.id])));
  document.querySelectorAll('.js-editar').forEach((b) => b.addEventListener('click', () => mostrarEdicion(fichas[b.dataset.id])));
  document.getElementById('detalleEditar').addEventListener('click', () => {
    cerrarModal(modalDetalle);
    if (fichaAbierta) mostrarEdicion(fichaAbierta);
  });
})();
