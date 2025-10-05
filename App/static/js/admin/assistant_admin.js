(function(){
  'use strict';

  function qs(sel, ctx){return (ctx||document).querySelector(sel);}  
  function qsa(sel, ctx){return Array.from((ctx||document).querySelectorAll(sel));}

  function notify(msg, type){
    if (typeof showNotification === 'function') { showNotification(msg, type); return; }
    console.log(`[Notification:${type}]`, msg);
  }

  function disableButton(btn, disabled){
    if(!btn) return;
    btn.disabled = !!disabled;
    btn.classList.toggle('disabled', !!disabled);
  }

  function showDeleteModal(username, triggerBtn){
    return new Promise(resolve => {
      const modal = qs('#deleteAssistantModal');
      if(!modal){ return resolve(false); }
      const msg = qs('#deleteAssistantMessage', modal);
      const cancelBtn = qs('#deleteAssistantCancel', modal);
      const confirmBtn = qs('#deleteAssistantConfirm', modal);
      if(msg){ msg.textContent = `Delete assistant "${username}"? This action is permanent and cannot be undone.`; }
      modal.style.display = 'flex';

      function cleanup(result){
        modal.style.display = 'none';
        cancelBtn.removeEventListener('click', onCancel);
        confirmBtn.removeEventListener('click', onConfirm);
        resolve(result);
      }
      function onCancel(e){ e.preventDefault(); cleanup(false); }
      function onConfirm(e){ e.preventDefault(); cleanup(true); }
      cancelBtn.addEventListener('click', onCancel);
      confirmBtn.addEventListener('click', onConfirm);
    });
  }

  async function deleteAssistant(username, button){
    if(!username) return;
    const proceed = await showDeleteModal(username, button);
    if(!proceed) return;

    disableButton(button, true);
    button.dataset.deleting = '1';
    const originalHtml = button.innerHTML;
    button.innerHTML = '<span class="material-icons">hourglass_top</span>';

    try {
      const res = await fetch(`/api/v2/admin/assistants/${encodeURIComponent(username)}`, {
        method: 'DELETE',
        headers: buildAuthHeaders(),
        credentials: 'same-origin'
      });
      const data = await res.json().catch(()=>({}));
      if(!res.ok || !data.success){
        const status = res.status;
        if (status === 409) {
            notify(data.message || 'Assistant has active time entry. Clock out first.', 'warning');
        } else {
            notify(data.message || `Failed (${status}) deleting assistant`, 'error');
        }
        return;
      }
      notify(data.message || 'Assistant deleted', 'success');
      const card = qs(`.staff-item[data-username="${username}"]`);
      if(card && card.parentNode){ card.parentNode.removeChild(card); }
    } catch (e){
      console.error(e);
      notify('Network or server error deleting assistant', 'error');
    } finally {
      if(button){
        button.removeAttribute('data-deleting');
        disableButton(button, false);
        button.innerHTML = originalHtml;
      }
    }
  }

  function wireDeleteButtons(){
    qsa('.delete-assistant-btn').forEach(btn => {
      btn.addEventListener('click', function(){
        if(this.dataset.deleting) return;
        const username = this.getAttribute('data-username');
        deleteAssistant(username, this);
      });
    });
  }

  document.addEventListener('DOMContentLoaded', wireDeleteButtons);
})();
