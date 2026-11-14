export default function ({data, parentElement, setTriggerValue}) {
  const root = parentElement.querySelector('.calendar');
  const focusKey = root.getRootNode().activeElement?.dataset?.focus;
  root.replaceChildren();
  function add(parent, tag, className, text) {
    const el = document.createElement(tag);
    el.className = className;
    if (text != null) el.textContent = text;
    parent.append(el);
    return el;
  }
  function picker(parent, key, iso, label, className, text) {
    const btn = add(parent, 'button', className, text);
    btn.type = 'button';
    btn.dataset.focus = key;
    btn.setAttribute('aria-label', label);
    btn.onclick = () => setTriggerValue('picked', iso);
    return btn;
  }
  const week = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const side = add(root, 'aside', 'agenda');
  add(side, 'h3', '', data.month + ' ' + data.year);
  const mini = add(side, 'div', 'mini');
  week.forEach(w => add(mini, 'small', '', w[0]));
  data.days.forEach(d => {
    if (!d.inMonth) return add(mini, 'span', '');
    const b = picker(mini, 'mini'+d.iso, d.iso, d.iso, 'miniDay', d.number);
    b.setAttribute('aria-pressed', String(d.iso === data.selected));
  });
  add(side, 'h4', '', data.dayLabel);
  const selected = data.days.find(d => d.iso === data.selected);
  if (!selected.events.length) add(side, 'p', '', 'No scheduled items');
  for (const e of selected.events) {
    const row = add(side, 'div', 'agendaItem '+e.kind);
    add(row, 'small', '', e.time);
    add(row, 'strong', '', e.title);
    if (e.detail) add(row, 'span', '', e.detail);
  }
  const main = add(root, 'section', 'sheet');
  const bar = add(main, 'div', 'toolbar');
  add(bar, 'strong', '', data.month + ' ' + data.year);
  const controls = add(bar, 'div', 'controls');
  picker(controls, 'prev', data.previous, 'Previous month', '', '‹');
  picker(controls, 'today', data.today, 'Go to today', '', 'Today');
  picker(controls, 'next', data.next, 'Next month', '', '›');
  const grid = add(main, 'div', 'month');
  week.forEach(w => add(grid, 'span', 'weekday', w));
  for (const d of data.days) {
    if (!d.inMonth) { add(grid, 'span', 'outside', d.number); continue; }
    const cell = picker(grid, 'day'+d.iso, d.iso, d.iso + ', '+d.events.length+' scheduled items', 'day');
    cell.setAttribute('aria-pressed', String(d.iso === data.selected));
    if (d.iso === data.today) cell.setAttribute('aria-current', 'date');
    add(cell, 'span', 'date', d.number);
    for (const e of d.events.slice(0,2)) add(cell, 'span', 'chip '+e.kind, e.title);
    if (d.events.length > 2) add(cell, 'small', 'more', '+'+(d.events.length-2));
    if (d.events.length) add(cell, 'span', 'marker', '•');
  }
  if (focusKey) Array.from(root.querySelectorAll('button')).find(b => b.dataset.focus === focusKey)?.focus({preventScroll:true});
}
