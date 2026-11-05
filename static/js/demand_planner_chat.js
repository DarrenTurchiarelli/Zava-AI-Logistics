(() => {
    'use strict';
    const context = JSON.parse(document.getElementById('planner-chat-context').textContent);
    const form = document.getElementById('planner-chat-form');
    const log = document.getElementById('planner-chat-log');
    const question = document.getElementById('planner-chat-question');
    const status = document.getElementById('planner-chat-status');
    const errorBox = document.getElementById('planner-chat-error');
    const send = document.getElementById('planner-chat-send');
    const clear = document.getElementById('planner-chat-clear');
    const examples = Array.from(document.querySelectorAll('.planner-chat-example'));
    const storageKey = `zava-planner-chat:${context.facility}:${context.horizon}`;
    const labels = {
        surge: 'Additional arrivals (%)', delay: 'Inbound truck delay (hours)',
        absence: 'Sort staff absent (%)', lane_outage: 'Sorting lanes unavailable',
        extra_staff: 'Extra afternoon sorters', extra_hours: 'Extra operating hours',
        transfer: 'Transfer reservation (parcels/day)', manual_mix: 'Manual-handling mix (%)'
    };
    const metrics = [
        ['arrivals', 'Expected arrivals'], ['peak_backlog', 'Peak backlog'],
        ['cutoff_misses', 'Dispatch-cutoff misses'], ['remaining', 'End backlog'],
        ['transferred', 'Transferred parcels'], ['cost', 'Incremental cost (AUD)'],
        ['recovery_hours', 'Drain-only recovery (hours)']
    ];
    let history = [];
    let storageAvailable = true;

    function showError(message) {
        errorBox.textContent = message;
        errorBox.classList.remove('d-none');
    }

    function message(role, text) {
        document.getElementById('planner-chat-welcome')?.remove();
        const wrapper = document.createElement('div');
        wrapper.className = `rounded p-3 mb-3 planner-chat-${role}`;
        const heading = document.createElement('strong');
        heading.textContent = role === 'user' ? 'You' : 'Planner';
        const body = document.createElement('div');
        body.className = 'planner-chat-message small mt-1';
        body.textContent = text;
        wrapper.append(heading, body);
        log.appendChild(wrapper);
        return wrapper;
    }

    function saveHistory() {
        history = history.slice(-8);
        if (!storageAvailable) return;
        try {
            sessionStorage.setItem(storageKey, JSON.stringify(history));
        } catch (error) {
            storageAvailable = false;
            console.warn('Planner chat browser history could not be saved.', error);
            showError('Browser chat history is unavailable. Chat still works, but messages may reset after navigation.');
        }
    }

    try {
        const saved = JSON.parse(sessionStorage.getItem(storageKey) || '[]');
        if (!Array.isArray(saved) || saved.some(item =>
            !['user', 'assistant'].includes(item.role) || typeof item.content !== 'string' ||
            item.content.length > 4000)) {
            throw new Error('Invalid stored planner conversation');
        }
        history = saved.slice(-8);
        history.forEach(item => message(item.role, item.content));
    } catch (error) {
        storageAvailable = false;
        console.warn('Planner chat browser history could not be restored.', error);
        showError('Browser chat history could not be restored. Start a new conversation below.');
    }

    function number(value) {
        return value === null ? '>72' : value.toLocaleString('en-AU');
    }

    function proposal(wrapper, data) {
        const heading = document.createElement('h3');
        heading.className = 'h6 mt-3';
        heading.textContent = 'Proposed scenario — not applied';
        const changes = document.createElement('ul');
        changes.className = 'small';
        Object.entries(data.changes).forEach(([name, value]) => {
            const item = document.createElement('li');
            item.textContent = `${labels[name]}: ${context.scenario[name]} → ${value}`;
            changes.appendChild(item);
        });
        const container = document.createElement('div');
        container.className = 'table-responsive';
        const table = document.createElement('table');
        table.className = 'table table-sm small';
        const head = document.createElement('thead');
        const headRow = document.createElement('tr');
        ['Engine-calculated measure', 'Current', 'Proposed'].forEach(label => {
            const cell = document.createElement('th');
            cell.scope = 'col';
            cell.textContent = label;
            headRow.appendChild(cell);
        });
        head.appendChild(headRow);
        const body = document.createElement('tbody');
        const facts = [];
        metrics.forEach(([key, label]) => {
            const row = document.createElement('tr');
            const name = document.createElement('th');
            name.scope = 'row';
            name.textContent = label;
            row.appendChild(name);
            [data.current[key], data.proposal[key]].forEach(value => {
                const cell = document.createElement('td');
                cell.textContent = number(value);
                row.appendChild(cell);
            });
            body.appendChild(row);
            facts.push(`${label}: current ${number(data.current[key])}; proposed ${number(data.proposal[key])}.`);
        });
        table.append(head, body);
        container.appendChild(table);
        const apply = document.createElement('a');
        apply.className = 'btn btn-sm btn-success';
        apply.textContent = 'Apply scenario to planner';
        apply.href = data.apply_url;
        const note = document.createElement('p');
        note.className = 'small text-muted mt-2 mb-0';
        note.textContent = `${data.source} Applying updates only this planning view. Preview valid for one hour.`;
        wrapper.append(heading, changes, container, apply, note);
        return `\nHistorical scenario preview: ${JSON.stringify(data.changes)}. Check the displayed inputs for the currently applied scenario.\nEngine results: ${facts.join(' ')}`;
    }

    examples.forEach(button => button.addEventListener('click', () => {
        question.value = button.dataset.question;
        question.focus();
    }));

    clear.addEventListener('click', () => {
        history = [];
        log.replaceChildren();
        errorBox.classList.add('d-none');
        saveHistory();
        message('assistant', 'Chat cleared. Ask about the currently displayed scenario.');
    });

    form.addEventListener('submit', async event => {
        event.preventDefault();
        const text = question.value.trim();
        if (!text || send.disabled) return;
        errorBox.classList.add('d-none');
        message('user', text);
        const previous = history.slice(-8);
        history.push({role: 'user', content: text});
        saveHistory();
        send.disabled = clear.disabled = question.disabled = true;
        examples.forEach(button => { button.disabled = true; });
        status.textContent = 'Asking Azure AI and calculating a scenario preview…';
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 65000);
        try {
            const response = await fetch(context.endpoint, {
                method: 'POST', credentials: 'same-origin', signal: controller.signal,
                headers: {'Content-Type': 'application/json', 'X-Planner-CSRF': context.csrf},
                body: JSON.stringify({snapshot: context.snapshot, message: text, history: previous})
            });
            if (response.redirected) throw new Error('Your session expired. Reload the page and sign in again.');
            if (!response.headers.get('content-type')?.includes('application/json')) {
                throw new Error('The chat service did not return a valid response. Reload the page and retry.');
            }
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'The planning chat request failed.');
            const wrapper = message('assistant', data.reply);
            const facts = data.proposal ? proposal(wrapper, data) : '';
            history.push({role: 'assistant', content: (data.reply + facts).slice(0, 4000)});
            saveHistory();
            question.value = '';
            log.scrollTop = log.scrollHeight;
            status.textContent = data.proposal ? 'Review the calculated preview, then choose Apply scenario.' :
                'No scenario changes proposed. Ask a follow-up question.';
        } catch (error) {
            showError(error.name === 'AbortError' ?
                'The AI request timed out. No scenario was changed. Please retry.' : error.message);
            status.textContent = 'Chat unavailable; manual scenario controls still work.';
        } finally {
            clearTimeout(timer);
            send.disabled = clear.disabled = question.disabled = false;
            examples.forEach(button => { button.disabled = false; });
            question.focus();
        }
    });
})();
