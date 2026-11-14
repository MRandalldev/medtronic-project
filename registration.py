"""A native browser form keeps the strength meter live as the patient types."""
import streamlit as st

account_fields = st.components.v2.component(
    "reco_accounts",
    html='<form><label>Email address<input type="email" name="email" autocomplete="email" required maxlength="254"></label><label>Password<input type="password" name="password" required maxlength="256"></label><section hidden><meter min="0" max="4" value="0"></meter><output aria-live="polite"></output><small>At least 6 characters, one number and one special character.</small><label>Confirm password<input type="password" name="confirm" autocomplete="new-password"></label><label>Your name<input name="name" autocomplete="given-name" maxlength="100"></label></section><button type="submit"></button></form>',
    css="""form{display:grid;gap:1rem;color:#203a45;font:1rem/1.45 system-ui}
    label,section:not([hidden]){display:grid;gap:.4rem}
    input{box-sizing:border-box;width:100%;min-width:0;height:3rem;border:1px solid #829baf;
    border-radius:.65rem;padding:.55rem .8rem;font:inherit;background:white;color:#16364c}
    input:focus-visible,button:focus-visible{outline:3px solid #397695;outline-offset:2px}
    button{justify-self:start;min-height:2.8rem;padding:.6rem 1.2rem;background:#175d7e;
    color:white;border:0;border-radius:.7rem;font:inherit;cursor:pointer}
    meter{width:100%;height:.8rem} small{margin-bottom:.45rem}""",
    js="""export default ({data,parentElement,setTriggerValue}) => {
      const form = parentElement.querySelector('form');
      const {email,password,confirm,name} = form.elements;
      const signup = data.signup;
      form.querySelector('section').hidden = !signup;
      name.required = confirm.required = signup;
      password.autocomplete = signup ? 'new-password' : 'current-password';
      form.querySelector('button').textContent = signup ? 'Create account' : 'Sign in';
      function validate() {
        const value = password.value;
        const rules = [value.length >= 6, /[0-9]/.test(value), /[^\\p{L}\\p{N}\\s]/u.test(value)];
        const met = rules.filter(Boolean).length;
        const score = met + Number(met === 3 && value.length >= 12);
        form.querySelector('meter').value = score;
        form.querySelector('output').textContent = value ? 'Password strength · ' + ['Weak','Weak','Weak','Medium','Strong'][score] : '';
        password.setCustomValidity(signup && met < 3 ? 'Use six characters, a number and a special character.' : '');
        confirm.setCustomValidity(signup && value !== confirm.value ? 'Passwords must match.' : '');
      }
      form.oninput = validate;
      form.onsubmit = event => {
        event.preventDefault();
        validate();
        if (form.reportValidity()) setTriggerValue('submit', {email:email.value,password:password.value,
          confirm:signup ? confirm.value : '',name:signup ? name.value : ''});
      };
    }""",
)
