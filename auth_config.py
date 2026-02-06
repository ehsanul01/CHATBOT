# auth_config.py

credentials = {
    "usernames": {
        "ehsanul": {
            "name": "Ehsanul Haque",
            "password": "chatbot123",   # plain text OK (auto-hash will handle)
        },
        "guest": {
            "name": "Guest User",
            "password": "guest123",
        },
    }
}

cookie_name = "chatbot_cookie"
cookie_key = "change_this_to_a_long_random_secret_key"
cookie_expiry_days = 7