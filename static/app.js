// Sistema de diagnóstico global (para no perder nada en producción)
window.onerror = function(msg, url, line, col, error) {
    console.error("Global Error: ", msg, error);
    showToast(`Error crítico: ${msg}`, 'error');
};

console.log("lulzVM UI: Inicializando...");

// --- i18n Language System ---

const LANGS = {
  en: {
    dashboard: 'Dashboard', vms: 'Virtual Machines', containers: 'Containers',
    storage: 'Storage', network: 'Network',
    node_overview: 'Node Overview', create_vm: '+ Create VM',
    storage_pools: 'Storage Pools', upload_iso: 'Upload ISO',
    available_isos: 'Available ISOs', net_config: 'Network Configuration',
    apply_changes: 'Apply Changes', phys_ifaces: 'Physical Interfaces',
    linux_bridges: 'Linux Bridges', create_bridge: '+ Create Bridge',
    create_vm_title: 'Create Virtual Machine', edit_vm_title: 'Edit Virtual Machine',
    upload_iso_title: 'Upload ISO File', create_bridge_title: 'Create Linux Bridge',
    cancel: 'Cancel', create: 'Create', save: 'Save Changes', upload: 'Upload',
    vm_id: 'VM ID', name: 'Name', memory: 'Memory (MB)', cores: 'CPU Cores',
    disk: 'Disk (GB)', iso_opt: 'ISO (optional)', boot_on_start: 'Boot on Start',
    bridge_name: 'Name', bridge_addr: 'CIDR Address (optional)',
    bridge_port: 'Bridge Port (Physical Interface)',
    iso_select: 'Select .iso file',
    status_running: 'running', status_stopped: 'stopped',
    action_start: 'Start', action_stop: 'Stop', action_reset: 'Reset',
    action_console: 'Console', action_edit: 'Edit', action_delete: 'Delete',
    confirm_delete: 'Delete VM', confirm_delete_msg: 'This will permanently delete VM',
    loading: 'Loading...', no_vms: 'No virtual machines. Create one to get started.',
    no_isos: 'No ISOs available.', no_bridges: 'No bridges configured.',
    iface_name: 'Name', iface_status: 'Status', iface_ip: 'IP',
    bridge_tbl_name: 'Name', bridge_tbl_addr: 'Address', bridge_tbl_ports: 'Ports',
    upload_failed: 'Upload failed. Check file size or permissions.',
    bridge_saved: 'Bridge saved. Remember to Apply Changes.',
    net_applied: 'Network configuration applied successfully.',
    err_loading_net: 'Error loading network:',
    err_loading_ifaces: 'Error loading interfaces.',
    vnc_loading: 'Starting VNC session...',
    community_msg: 'lulzVM is open source — feel free to contribute, modify and improve it. Together we build something powerful.',
    community_link: 'Contribute on GitHub',
  },
  es: {
    dashboard: 'Panel', vms: 'Máquinas Virtuales', containers: 'Contenedores',
    storage: 'Almacenamiento', network: 'Red',
    node_overview: 'Resumen del Nodo', create_vm: '+ Crear VM',
    storage_pools: 'Pools de Almacenamiento', upload_iso: 'Subir ISO',
    available_isos: 'ISOs Disponibles', net_config: 'Configuración de Red',
    apply_changes: 'Aplicar Cambios', phys_ifaces: 'Interfaces Físicas',
    linux_bridges: 'Linux Bridges', create_bridge: '+ Crear Bridge',
    create_vm_title: 'Crear Máquina Virtual', edit_vm_title: 'Editar Máquina Virtual',
    upload_iso_title: 'Subir archivo ISO', create_bridge_title: 'Crear Linux Bridge',
    cancel: 'Cancelar', create: 'Crear', save: 'Guardar Cambios', upload: 'Subir',
    vm_id: 'ID de VM', name: 'Nombre', memory: 'Memoria (MB)', cores: 'Núcleos CPU',
    disk: 'Disco (GB)', iso_opt: 'ISO (opcional)', boot_on_start: 'Iniciar con el sistema',
    bridge_name: 'Nombre', bridge_addr: 'Dirección CIDR (opcional)',
    bridge_port: 'Puerto del Bridge (Interfaz Física)',
    iso_select: 'Seleccionar archivo .iso',
    status_running: 'corriendo', status_stopped: 'detenida',
    action_start: 'Iniciar', action_stop: 'Detener', action_reset: 'Reiniciar',
    action_console: 'Consola', action_edit: 'Editar', action_delete: 'Borrar',
    confirm_delete: 'Borrar VM', confirm_delete_msg: 'Esto eliminará permanentemente la VM',
    loading: 'Cargando...', no_vms: 'Sin máquinas virtuales. Crea una para empezar.',
    no_isos: 'No hay ISOs disponibles.', no_bridges: 'No hay bridges configurados.',
    iface_name: 'Nombre', iface_status: 'Estado', iface_ip: 'IP',
    bridge_tbl_name: 'Nombre', bridge_tbl_addr: 'Dirección', bridge_tbl_ports: 'Puertos',
    upload_failed: 'Subida fallida. Verifica el tamaño o permisos.',
    bridge_saved: 'Bridge guardado. Recuerda Aplicar Cambios.',
    net_applied: 'Configuración de red aplicada exitosamente.',
    err_loading_net: 'Error cargando red:',
    err_loading_ifaces: 'Error cargando interfaces.',
    vnc_loading: 'Iniciando sesión VNC...',
    community_msg: 'lulzVM es open source — siéntete libre de contribuir, modificar y mejorar. Juntos construimos algo poderoso.',
    community_link: 'Contribuir en GitHub',
  }
};

let currentLang = localStorage.getItem('lulzvm_lang') || 'en';
function t(key) { return LANGS[currentLang][key] || LANGS['en'][key] || key; }

function setLang(lang) {
  currentLang = lang;
  localStorage.setItem('lulzvm_lang', lang);
  applyTranslations();
}

function applyTranslations() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll('[data-i18n-ph]').forEach(el => {
    el.placeholder = t(el.dataset.i18nPh);
  });
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    el.title = t(el.dataset.i18nTitle);
  });
  document.getElementById('lang-selector')?.querySelectorAll('button').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === currentLang);
  });
}

const API = '';


// --- UI / UX Utilities ---

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">${message}</div>
        <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
    `;
    container.appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if(toast.parentElement) toast.remove();
    }, 5000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
    return container;
}

function setBtnLoading(btn, isLoading, text = 'Loading...') {
    if (isLoading) {
        btn.dataset.originalText = btn.innerHTML;
        btn.innerHTML = `<span class="spinner"></span> ${text}`;
        btn.disabled = true;
        btn.classList.add('btn-loading');
    } else {
        btn.innerHTML = btn.dataset.originalText;
        btn.disabled = false;
        btn.classList.remove('btn-loading');
    }
}

// --- API Core ---

async function api(method, path, body = null) {
  const headers = { 'Content-Type': 'application/json' };
  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);
  
  const res = await fetch(`${API}${path}`, opts);
  if (!res.ok) {
    let errDetail = `HTTP ${res.status}`;
    try {
        const err = await res.json();
        errDetail = err.detail || errDetail;
    } catch(e) {}
    throw new Error(errDetail);
  }
  if (res.status === 204) return null;
  return res.json();
}

// --- Navigation ---

async function initApp() {
  document.querySelectorAll('.nav-item[data-view]').forEach(el => {
    el.addEventListener('click', e => {
      e.preventDefault();
      switchView(el.dataset.view);
    });
  });
  applyTranslations();
  await loadDashboard();
}

function switchView(view) {
  document.querySelectorAll('.view').forEach(v => v.style.display = 'none');
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById(`view-${view}`).style.display = 'block';
  document.querySelector(`[data-view="${view}"]`)?.classList.add('active');
  
  if (view === 'vms') loadVMs();
  if (view === 'storage') loadStorage();
  if (view === 'network') loadNetwork();
}

// --- Dashboard ---

async function loadDashboard() {
  try {
    const node = await api('GET', '/api/nodes/');
    if (!node) return;
    const sg = document.getElementById('node-stats');
    sg.innerHTML = [
        stat('CPU', node.cpu_usage + '%', node.cpu_count + ' cores'),
        stat('Memory', node.mem_used_gb + ' / ' + node.mem_total_gb + ' GB', node.mem_percent + '%'),
        stat('Disk', node.disk_used_gb + ' / ' + node.disk_total_gb + ' GB', ''),
        stat('KVM', node.kvm_available ? 'Available' : 'Not available', node.qemu_version),
    ].join('');

    const vms = await api('GET', '/api/vms/');
    document.getElementById('vm-table-container').innerHTML = vmTable(vms || []);
  } catch(e) {
    showToast(`Error loading dashboard: ${e.message}`, 'error');
  }
}

function stat(label, value, sub) {
  return `<div class="stat-card"><div class="stat-label">${label}</div>
    <div class="stat-value">${value}</div>
    <div class="stat-sub">${sub}</div></div>`;
}

// --- Virtual Machines ---

async function loadVMs() {
    try {
        const vms = await api('GET', '/api/vms/') || [];
        document.getElementById('vms-list').innerHTML = vmTable(vms);
    } catch(e) {
        showToast(`Error listing VMs: ${e.message}`, 'error');
    }
}

function vmTable(vms) {
  if (!vms.length) return '<p class="empty">No VMs found. Create one to get started.</p>';
  return `<table class="data-table"><thead>
    <tr><th>VMID</th><th>Name</th><th>Status</th><th>Memory</th><th>Cores</th><th>Actions</th></tr>
    </thead><tbody>${vms.map(vm => `
    <tr>
      <td>${vm.vmid}</td>
      <td>${vm.name}</td>
      <td><span class="badge badge-${vm.status}">${vm.status}</span></td>
      <td>${vm.memory_mb} MB</td>
      <td>${vm.cores}</td>
      <td class="actions" id="vm-actions-${vm.vmid}">
        ${vm.status === 'stopped' || vm.status === 'error'
          ? `<button class="btn-sm btn-green" onclick="vmAction(this, ${vm.vmid},'start')">Start</button>`
          : `<button class="btn-sm btn-red"   onclick="vmAction(this, ${vm.vmid},'stop')">Stop</button>
             <button class="btn-sm"           onclick="vmAction(this, ${vm.vmid},'reset')">Reset</button>
             <button class="btn-sm btn-accent" onclick="showConsole(${vm.vmid}, '${vm.name}')">Console</button>`}
        <button class="btn-sm" onclick="showEditVMModal(${vm.vmid})">Edit</button>
        <button class="btn-sm btn-danger" onclick="deleteVM(this, ${vm.vmid})">Delete</button>
      </td>
    </tr>`).join('')}</tbody></table>`;
}

async function vmAction(btn, vmid, action) {
  setBtnLoading(btn, true, action === 'start' ? 'Booting...' : 'Stopping...');
  try {
    await api('POST', `/api/vms/${vmid}/${action}`);
    showToast(`VM ${vmid}: ${action} command sent successfully`, 'success');
    await loadVMs();
    if (document.getElementById('view-dashboard').style.display !== 'none') await loadDashboard();
  } catch(e) {
      showToast(`Error (${action} VM ${vmid}): ${e.message}`, 'error');
      setBtnLoading(btn, false);
  }
}

async function deleteVM(btn, vmid) {
  if (!confirm(`Delete VM ${vmid}? This cannot be undone.`)) return;
  setBtnLoading(btn, true, 'Deleting...');
  try {
    await api('DELETE', `/api/vms/${vmid}`);
    showToast(`VM ${vmid} deleted successfully.`, 'success');
    await loadVMs();
  } catch(e) {
      showToast(`Error deleting VM ${vmid}: ${e.message}`, 'error');
      setBtnLoading(btn, false);
  }
}

function closeModal(id) {
    document.getElementById(id).style.display = 'none';
}

async function showCreateVMModal() {
  try {
      const isos = await api('GET', '/api/storage/isos') || [];
      const select = document.getElementById('new-iso-select');
      select.innerHTML = '<option value="">None</option>' +
        isos.map(iso => `<option value="/var/lib/lulzvm/images/${iso}">${iso}</option>`).join('');
      document.getElementById('modal-create-vm').style.display = 'flex';
  } catch(e) {
      showToast('Error loading ISOs.', 'error');
  }
}

async function doCreateVM() {
  const btn = document.querySelector('#modal-create-vm .btn-primary');
  setBtnLoading(btn, true, 'Creating...');
  
  try {
    const vmid  = parseInt(document.getElementById('new-vmid').value);
    const name  = document.getElementById('new-name').value;
    const mem   = parseInt(document.getElementById('new-mem').value);
    const cores = parseInt(document.getElementById('new-cores').value);
    const disk  = parseInt(document.getElementById('new-disk').value);

    const filename = `vm-${vmid}-disk-0.qcow2`;
    
    // Primero crear disco
    await api('POST', '/api/storage/create-disk', {
      pool_id: 'local', filename, size_gb: disk, format: 'qcow2'
    });
    
    // Luego registrar VM
    await api('POST', '/api/vms/', {
      vmid, name, memory_mb: mem, cores,
      disks: [{ id:'scsi0', bus:'virtio', storage:'local', file: filename, size_gb: disk, cache:'none', aio:'io_uring' }],
      nics:  [{ id:'net0', model:'virtio', bridge:'lulzbr0', mac:'', vlan:0 }],
      cdrom: document.getElementById('new-iso-select').value || null,
    });
    
    showToast(`VM ${vmid} created successfully.`, 'success');
    closeModal('modal-create-vm');
    await loadVMs();
  } catch(e) {
      showToast(`Error creating VM: ${e.message}`, 'error');
  } finally {
      setBtnLoading(btn, false);
  }
}

// --- Modals and ISO Management ---

async function showEditVMModal(vmid) {
    try {
      const vm = await api('GET', `/api/vms/${vmid}`);
      const isos = await api('GET', '/api/storage/isos') || [];
      
      document.getElementById('edit-vmid').value = vmid;
      document.getElementById('edit-name').value = vm.vm.name;
      document.getElementById('edit-mem').value  = vm.hardware.memory_mb;
      document.getElementById('edit-cores').value = vm.hardware.cores;
      document.getElementById('edit-onboot').checked = vm.options.onboot;
      
      const select = document.getElementById('edit-iso-select');
      select.innerHTML = '<option value="">None</option>' + 
        isos.map(iso => `<option value="/var/lib/lulzvm/images/${iso}" ${vm.boot.cdrom.includes(iso) ? 'selected' : ''}>${iso}</option>`).join('');
        
      document.getElementById('modal-edit-vm').style.display = 'flex';
    } catch(e) {
        showToast(`Error loading VM details: ${e.message}`, 'error');
    }
}

async function doUpdateVM() {
  const btn = document.querySelector('#modal-edit-vm .btn-primary');
  setBtnLoading(btn, true, 'Saving...');
  try {
    const vmid = document.getElementById('edit-vmid').value;
    const data = {
      name:      document.getElementById('edit-name').value,
      memory_mb: parseInt(document.getElementById('edit-mem').value),
      cores:     parseInt(document.getElementById('edit-cores').value),
      cdrom:     document.getElementById('edit-iso-select').value || "",
      onboot:    document.getElementById('edit-onboot').checked
    };
    await api('PUT', `/api/vms/${vmid}`, data);
    showToast('VM updated successfully.', 'success');
    closeModal('modal-edit-vm');
    await loadVMs();
  } catch(e) {
      showToast(`Error updating VM: ${e.message}`, 'error');
  } finally {
      setBtnLoading(btn, false);
  }
}

async function loadStorage() {
  try {
      const pools = await api('GET', '/api/storage/') || [];
      document.getElementById('storage-list').innerHTML =
        pools.map(p => `<div class="stat-card">
          <div class="stat-label">${p.id}</div>
          <div class="stat-value">${p.name}</div>
          <div class="stat-sub">${p.type} — ${p.path || p.dataset || ''}</div>
        </div>`).join('');
        
      const isos = await api('GET', '/api/storage/isos') || [];
      document.getElementById('iso-list').innerHTML = 
        isos.map(iso => `<div class="stat-card">
          <div class="stat-label">ISO Image</div>
          <div class="stat-value" style="font-size: 1rem; word-break: break-all;">${iso}</div>
        </div>`).join('');
  } catch (e) {
      showToast(`Error loading storage: ${e.message}`, 'error');
  }
}

function showUploadISOModal() {
  document.getElementById('modal-upload-iso').style.display = 'flex';
}

async function doUploadISO() {
  const fileInput = document.getElementById('iso-file');
  if (!fileInput.files.length) {
      showToast('Please select an ISO file', 'error');
      return;
  }
  
  const file = fileInput.files[0];
  const formData = new FormData();
  formData.append('file', file);
  
  const btn = document.getElementById('btn-do-upload');
  const progress = document.getElementById('upload-progress');
  const progressBar = document.getElementById('upload-progress-bar');
  
  setBtnLoading(btn, true, 'Uploading...');
  progress.style.display = 'block';
  
  const xhr = new XMLHttpRequest();
  xhr.open('POST', `${API}/api/storage/upload-iso`);
  
  xhr.upload.onprogress = (e) => {
    if (e.lengthComputable) {
      const pct = Math.round((e.loaded / e.total) * 100);
      progressBar.style.width = pct + '%';
    }
  };
  
  xhr.onload = async () => {
    setBtnLoading(btn, false);
    progress.style.display = 'none';
    progressBar.style.width = '0%';
    if (xhr.status === 201) {
      showToast('ISO uploaded successfully.', 'success');
      closeModal('modal-upload-iso');
      await loadStorage();
    } else {
      showToast('Upload failed. Check file size or permissions.', 'error');
    }
  };
  
  xhr.send(formData);
}

// --- Network ---

async function loadNetwork() {
  try {
      const ifaces = await api('GET', '/api/network/interfaces') || [];
      const bridges = await api('GET', '/api/network/bridges') || [];
      
      document.getElementById('interfaces-list').innerHTML = `<table class="data-table"><thead>
        <tr><th>Name</th><th>Status</th><th>IP</th></tr></thead><tbody>
        ${ifaces.map(i => `<tr><td>${i.name}</td><td>${i.isup ? '<span class="badge badge-running">UP</span>' : '<span class="badge badge-stopped">DOWN</span>'}</td><td>${i.ip || '-'}</td></tr>`).join('')}
        </tbody></table>`;
        
      document.getElementById('bridges-list').innerHTML = `<table class="data-table"><thead>
        <tr><th>Name</th><th>Address</th><th>Ports</th></tr></thead><tbody>
        ${bridges.map(b => `<tr><td>${b.name}</td><td>${b.address || '-'}</td><td>${b.interfaces.join(', ') || '-'}</td></tr>`).join('')}
        ${bridges.length === 0 ? '<tr><td colspan="3">No bridges configured</td></tr>' : ''}
        </tbody></table>`;
  } catch(e) {
      showToast(`Error loading network: ${e.message}`, 'error');
  }
}

async function showCreateBridgeModal() {
  try {
      const ifaces = await api('GET', '/api/network/interfaces') || [];
      const select = document.getElementById('new-bridge-ports');
      select.innerHTML = '<option value="">None</option>' + 
        ifaces.map(i => `<option value="${i.name}">${i.name}</option>`).join('');
      document.getElementById('modal-create-bridge').style.display = 'flex';
  } catch(e) {
      showToast('Error loading interfaces.', 'error');
  }
}

async function doCreateBridge() {
  try {
      const name = document.getElementById('new-bridge-name').value;
      const addr = document.getElementById('new-bridge-addr').value;
      const port = document.getElementById('new-bridge-ports').value;
      
      const bridges = await api('GET', '/api/network/bridges') || [];
      bridges.push({
          name: name,
          address: addr || null,
          autostart: true,
          interfaces: port ? [port] : []
      });
      
      await api('POST', '/api/network/bridges', { bridges });
      showToast('Bridge saved. Remember to Apply Changes.', 'success');
      closeModal('modal-create-bridge');
      await loadNetwork();
  } catch(e) {
      showToast(`Error: ${e.message}`, 'error');
  }
}

async function applyNetwork() {
  try {
      await api('POST', '/api/network/apply');
      showToast('Network configuration applied successfully.', 'success');
      await loadNetwork();
  } catch(e) {
      showToast(`Error applying network: ${e.message}`, 'error');
  }
}

// --- VNC Console ---

async function showConsole(vmid, name) {
  document.getElementById('console-title').textContent = `Console: ${name} (ID: ${vmid})`;
  const container = document.getElementById('noVNC_container');
  container.innerHTML = '<div class="spinner" style="border-width: 3px; border-top-color: var(--accent); width: 40px; height: 40px; margin: 0 auto;"></div><p style="color: var(--text2); margin-top: 1rem; text-align: center;">Starting VNC session...</p>';
  document.getElementById('modal-console').style.display = 'flex';

  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const wsUrl = `${protocol}://${window.location.host}/api/vms/${vmid}/vnc`;

  if (!window.RFB) {
    try {
      const mod = await import('https://cdn.jsdelivr.net/npm/@novnc/novnc/core/rfb.js');
      window.RFB = mod.default;
    } catch (e) {
      container.innerHTML = `<p style="color: var(--red); text-align: center;"><strong>Critical Error:</strong> Could not load VNC module.</p>`;
      showToast('Failed to load noVNC library.', 'error');
      return;
    }
  }

  _startRFB(window.RFB, container, wsUrl);
}

function _startRFB(RFB, container, wsUrl) {
  try {
    container.innerHTML = '';
    const rfb = new RFB(container, wsUrl);
    rfb.scaleViewport = true;
    rfb.resizeSession = true;
    
    rfb.addEventListener('disconnect', (e) => {
      if (document.getElementById('modal-console').style.display !== 'none') {
        container.innerHTML = `<p style="color: var(--red); text-align: center; font-weight: bold;">[VNC] Disconnected by server.</p>`;
      }
    });
    rfb.addEventListener('connect', () => {
      console.log(`[VNC] Connection established to ${wsUrl}`);
    });
  } catch (e) {
    container.innerHTML = `<p style="color: var(--red); text-align: center;">Error VNC local: ${e.message}</p>`;
    showToast(`Error al inicializar consola: ${e.message}`, "error");
  }
}

Object.assign(window, {
    closeModal, switchView, loadDashboard, loadVMs,
    loadStorage, vmAction, deleteVM, showCreateVMModal, doCreateVM,
    showEditVMModal, doUpdateVM, showUploadISOModal, doUploadISO, showConsole,
    loadNetwork, showCreateBridgeModal, doCreateBridge, applyNetwork,
    setLang
});

// Init
window.addEventListener('DOMContentLoaded', () => {
    initApp();
    switchView('dashboard');
});
