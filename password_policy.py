"""
password_policy.py: one password rule for the browser meter and the server.
NIST SP 800-63B-4 (sec. 3.1.1.2): at least 8 characters when a second factor is used
(Reco signs in with password + emailed code), allow 64+, no composition rules
(no forced numbers/symbols), and reject commonly used or compromised passwords.
https://pages.nist.gov/800-63-4/sp800-63b.html
"""
MIN_LEN, MAX_LEN = 8, 256

# Most common passwords from public breach lists (kept short; extend freely).
COMMON = sorted(set("""
123456 123456789 12345678 password qwerty123 qwerty 1q2w3e4r 111111 123123 1234567890
00000000 11111111 12341234 87654321 abc12345 abcd1234 password1 password123 passw0rd
p@ssw0rd p@ssword iloveyou sunshine princess football baseball welcome welcome1 monkey123
dragon123 letmein letmein1 trustno1 admin123 administrator qwertyuiop asdfghjkl zxcvbnm1
superman batman123 starwars computer whatever freedom shadow123 master123 michael1 jennifer
jordan23 charlie1 hello123 iloveyou1 changeme secret123 summer2024 summer2025 summer2026
winter2025 winter2026 fall2026 spring2026 heart123 recovery recovery1 hospital medtronic
reco1234 aggies123 ncat1234 aggiepride
""".split()))


def score(password: str, email: str = "") -> tuple:
    """Return (0-4, label, problem). 0 = not allowed. Same math as the JS meter."""
    pw = password or ""
    low = pw.casefold()
    name = email.split("@")[0].casefold() if email else ""
    if len(pw) < MIN_LEN:
        return 0, "Too short", f"Use at least {MIN_LEN} characters."
    if len(pw) > MAX_LEN:
        return 0, "Too long", f"Use at most {MAX_LEN} characters."
    if low in COMMON or len(set(low)) <= 2 or (len(name) >= 4 and name in low):
        return 0, "Too common", "That password is too common or too easy to guess. Try a short phrase of a few words."
    s = 1 if len(pw) < 10 else 2 if len(pw) < 12 else 3 if len(pw) < 15 else 4
    kinds = sum([any(c.islower() for c in pw), any(c.isupper() for c in pw),
                 any(c.isdigit() for c in pw), any(not c.isalnum() for c in pw)])
    if kinds >= 3 and s < 4:
        s += 1
    return s, ["Too short", "Weak", "Fair", "Good", "Strong"][s], ""
