(() => {
    'use strict';
    const context = JSON.parse(document.getElementById('network-chat-context').textContent);
    const status = document.getElementById('network-status');
    function show(message, failed = false) {
        status.textContent = message;
        status.className = `alert alert-${failed ? 'danger' : 'info'} alert-persistent`;
        status.scrollIntoView({block: 'nearest'});
    }
    async function read(response) {
        if (response.redirected) throw new Error('Sign in again before continuing.');
        if (!response.headers.get('content-type')?.includes('application/json')) {
            throw new Error('The server did not return a valid result. Reload and check the saved decision before retrying.');
        }
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'The request failed; no success was confirmed.');
        return data;
    }
    document.querySelectorAll('.demo-decision-form').forEach(form => {
        form.addEventListener('submit', async event => {
            event.preventDefault();
            const button = event.submitter;
            const fields = new FormData(form);
            if (button?.name) fields.set(button.name, button.value);
            const buttons = Array.from(form.querySelectorAll('button'));
            const disabled = buttons.map(item => item.disabled);
            buttons.forEach(item => { item.disabled = true; });
            try {
                const data = await read(await fetch(form.getAttribute('action'), {method: 'POST', body: fields, credentials: 'same-origin'}));
                show(`${data.message} Status: ${data.plan.status}. Reloading the audit view…`);
                window.location.reload();
            } catch (error) {
                show(error.message, true);
                buttons.forEach((item, index) => { item.disabled = disabled[index]; });
            }
        });
    });
    const form = document.getElementById('network-chat-form');
    const button = document.getElementById('network-chat-send');
    const result = document.getElementById('network-chat-result');
    form.addEventListener('submit', async event => {
        event.preventDefault();
        const message = document.getElementById('network-chat-question').value.trim();
        if (!message || button.disabled) return;
        button.disabled = true;
        result.classList.remove('text-danger');
        result.textContent = 'The dedicated agent is inspecting the network snapshot and running planning tools…';
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 65000);
        try {
            const data = await read(await fetch(context.endpoint, {
                method: 'POST', credentials: 'same-origin', signal: controller.signal,
                headers: {'Content-Type': 'application/json', 'X-Planner-CSRF': context.csrf},
                body: JSON.stringify({snapshot: context.snapshot, message})
            }));
            result.replaceChildren();
            const reply = document.createElement('p');
            reply.textContent = data.reply;
            result.appendChild(reply);
            if (data.proposal) {
                const figures = document.createElement('p');
                figures.textContent = `Calculated preview — not applied. Forecast: ${data.proposal.totals.forecast.toLocaleString('en-AU')} parcels. ` +
                    `Focus constraint: ${data.proposal.selected.constraint.toLocaleString('en-AU')}. ` +
                    `Priority exposure proxy: ${data.proposal.selected.priority_exposure.toLocaleString('en-AU')}.`;
                const apply = document.createElement('a');
                apply.className = 'btn btn-outline-primary';
                apply.href = data.apply_url;
                apply.textContent = 'Apply scenario preview (no approval or execution)';
                result.append(figures, apply);
            }
        } catch (error) {
            result.textContent = error.name === 'AbortError' ? 'Agent request timed out; no decision was changed.' : error.message;
            result.classList.add('text-danger');
        } finally {
            clearTimeout(timer);
            button.disabled = false;
        }
    });
})();
