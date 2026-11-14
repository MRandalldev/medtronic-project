"""quiz.py: the one-question-per-screen look shared by the profile and the daily check-in."""
import streamlit as st

OTHER, NONE = "Other", "None of these"


def header(label: str, index: int, total: int, back_key: str) -> bool:
    """Back arrow + diamond progress track. Returns True when Back was pressed."""
    top = st.columns([1, 7], vertical_alignment="center")
    back = index > 0 and top[0].button("←", key=back_key, help="Back to the previous question")
    dots = "".join(f'<span class="dot{" done" if i <= index else ""}" style="left:{(i + 1) * 100 / total - 0.01:.2f}%"></span>'
                   for i in range(total))
    top[1].html(f'<div class="quiz-progress" role="img" aria-label="Question {index + 1} of {total}">'
                f'<span class="label">{label} · {index + 1} OF {total}</span>'
                f'<div class="track"><div class="fill" style="transform:scaleX({(index + 1) / total:.3f})"></div>{dots}</div></div>')
    return bool(back)


def question(text: str, hint: str = "") -> None:
    st.html(f'<h2 class="quiz-question">{text}</h2>' + (f'<p class="quiz-hint">{hint}</p>' if hint else ""))


def choice(label: str, options: list, current, key: str, other_label: str = "Type your answer"):
    """Single choice as tiles, always with Other. Returns the chosen text ('' when nothing is picked yet)."""
    options = list(dict.fromkeys(options + [OTHER]))
    known = current if current in options else (OTHER if current else None)
    picked = st.radio(label, options, index=options.index(known) if known else None, key=key, label_visibility="collapsed")
    if picked == OTHER:
        typed = st.text_input(other_label, current if current not in options else "", key=key + "_other")
        return typed.strip()
    return picked or ""


def ticks(items: list, chosen, key: str, columns: int = 1) -> set | None:
    """Multi-select tiles with a 'None of these' tile. Returns the chosen ids, an empty set for None,
    or None when nothing was tapped yet. items = [(id, text)]."""
    picked = set()
    cols = st.columns(columns) if columns > 1 else [st.container()]
    for n, (item_id, text) in enumerate(items):
        if cols[n % len(cols)].checkbox(text, value=item_id in (chosen or ()), key=f"{key}_{item_id}"):
            picked.add(item_id)
    none = st.checkbox(NONE, value=chosen == set(), key=f"{key}__none")
    if picked:
        return picked
    return set() if none else None
