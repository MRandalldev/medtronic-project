"""A native browser form keeps the strength meter live as the patient types."""
import streamlit as st

account_fields = st.components.v2.component(
    "reco_accounts",
    html='<form><label>Email address<input type="email" name="email" autocomplete="email" required maxlength="254"></label><label>Password<input type="password" name="password" required maxlength="256" minlength="0"></label><section hidden><meter min="0" max="4" low="1.5" high="2.5" optimum="4" value="0"></meter><output aria-live="polite"></output><small>At least 8 characters. A short phrase of a few words is easy to remember and hard to guess.</small><label>Confirm password<input type="password" name="confirm" autocomplete="new-password"></label><label>Your name<input name="name" autocomplete="given-name" maxlength="100"></label></section><button type="submit"></button></form>',
    css="""form{display:grid;gap:.65rem;color:var(--ink,#203a45);font:1rem/1.45 "Atkinson Hyperlegible",system-ui}
    label,section:not([hidden]){display:grid;gap:.4rem}
    input{box-sizing:border-box;width:100%;min-width:0;height:3rem;border:1px solid var(--line-strong,#829baf);
    border-radius:12px;transition:border-color 200ms ease,box-shadow 200ms ease;padding:.55rem .8rem;font:inherit;background:white;color:#16364c}
    input:focus{outline:none;border-color:var(--accent,#2a4fd6);box-shadow:0 0 0 4px var(--accent-ring,#2a4fd640)} button:focus-visible{outline:3px solid var(--accent,#2a4fd6);outline-offset:2px}
    button{width:100%;min-height:2.8rem;padding:.6rem 1.2rem;background:var(--grad,#2a4fd6);box-shadow:0 1px 2px #0002,0 8px 20px -8px #3d4fe099;
    color:white;border:0;border-radius:12px;transition:transform 140ms cubic-bezier(0.23,1,0.32,1),box-shadow 200ms ease;font:inherit;font-weight:650;cursor:pointer}
    button:active{transform:scale(.97)} button:disabled{opacity:.6;cursor:default} form{color:var(--reco-ink,inherit)} input{color:var(--ink,inherit);background:var(--field,transparent)} meter{width:100%;height:.8rem} small{margin-bottom:.45rem}""",
    js="""export default ({data,parentElement,setTriggerValue}) => {
      const form = parentElement.querySelector('form');
      const {email,password,confirm,name} = form.elements;
      const signup = data.signup;
      form.querySelector('button').disabled = data.disabled;
      form.querySelector('section').hidden = !signup;
      name.required = confirm.required = signup;
      password.autocomplete = signup ? 'new-password' : 'current-password';
      form.querySelector('button').textContent = signup ? 'Create account' : 'Sign in';
      function validate() {
        const value = password.value;
        const low = value.toLowerCase(), who = email.value.split('@')[0].toLowerCase();
        let score = 0, problem = '';
        if (value.length < 8) problem = 'Use at least 8 characters.';
        else if (data.common.includes(low) || new Set(low).size <= 2 || (who.length >= 4 && low.includes(who)))
          problem = 'That password is too common or too easy to guess. Try a short phrase of a few words.';
        else {
          score = value.length < 10 ? 1 : value.length < 12 ? 2 : value.length < 15 ? 3 : 4;
          const kinds = [/[a-z]/, /[A-Z]/, /[0-9]/, /[^A-Za-z0-9]/].filter(r => r.test(value)).length;
          if (kinds >= 3 && score < 4) score += 1;
        }
        form.querySelector('meter').value = score;
        form.querySelector('output').textContent = value ? 'Password strength · ' + (problem && value.length >= 8 ? 'Too common' : ['Too short','Weak','Fair','Good','Strong'][score]) : '';
        password.setCustomValidity(signup && problem ? problem : '');
        confirm.setCustomValidity(signup && value !== confirm.value ? 'Passwords must match.' : '');
      }
      form.oninput = validate;
      form.onsubmit = event => {
        event.preventDefault();
        if (data.disabled) return;
        validate();
        if (form.reportValidity()) setTriggerValue('submit', {email:email.value,password:password.value,
          confirm:signup ? confirm.value : '',name:signup ? name.value : ''});
      };
    }""",
)
