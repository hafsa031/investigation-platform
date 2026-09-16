# SYNTHETIC incident report MGMT-1042 (safe test data)

## Summary
User downloaded `invoice.exe` from `http://files.evil-example.tk/invoice.exe`.
SHA256: `ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad`

## Phishing vector
Defanged link found in mailbox: `hxxp://acme-portal-secure[.]net/login?session=abc123`
Sender: `attacker@evil-example.tk` (SPF fail).

## Auth trail
14 failed SSH logins for `root` from `198.51.100.23`, then one success.
Internal sensor `127.0.0.1` also logged (must stay LOW).
