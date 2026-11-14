export default function ({data, parentElement, setTriggerValue}) {
  const grid = parentElement.querySelector('.month');
  const previousFocus = grid.getRootNode().activeElement?.dataset?.day;
  grid.replaceChildren();
  for (const label of ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']) {
    const heading = document.createElement('span');
    heading.className = 'weekday';
    heading.textContent = label;
    grid.append(heading);
  }
  for (const day of data.days) {
    if (!day.inMonth) {
      grid.append(document.createElement('span'));
      continue;
    }
    const cell = document.createElement('button');
    cell.type = 'button';
    cell.dataset.day = day.iso;
    cell.textContent = day.number;
    cell.setAttribute('aria-pressed', String(data.selected === day.iso));
    if (day.today) cell.setAttribute('aria-current', 'date');
    const events = day.events.length;
    cell.setAttribute('aria-label', day.iso + (events ? ', ' + events + ' scheduled items' : ', no scheduled items'));
    if (events) {
      const marker = document.createElement('small');
      marker.textContent = events;
      cell.append(marker);
      cell.title = day.events.join(' · ');
    }
    cell.onclick = () => setTriggerValue('picked', day.iso);
    grid.append(cell);
    if (previousFocus === day.iso) cell.focus();
  }
}
