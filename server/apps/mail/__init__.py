"""Mail app — an isolated mail client living at the ``/mail`` route family.

Owns its own store (:class:`server.apps.mail.state.MailState`). Mutations
touch ONLY that store; cross-app effects (a shop order producing a
confirmation email) arrive through the event bus, never by another app
writing here directly.
"""
