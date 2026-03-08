# Telegram Obunachi Savdo Bot

Bu Telegram bot kanallarga obuna bo'lish orqali pul ishlash va kanal egalari uchun obunachi sotib olish imkoniyatini beradi.

## Xususiyatlar

- Foydalanuvchi ro'yxatdan o'tish va referral tizimi
- Kanallarga obuna bo'lib pul ishlash vazifalari
- Kanalga obunachi sotib olish buyurtmalari
- Balans va tranzaksiya boshqaruvi
- Kunlik bonus tizimi
- Pul yechish tizimi
- Admin panel boshqaruvi
- Firibgarlikka qarshi choralari

## O'rnatish

1. Repozitoriyani klonlang
2. Kutubxonalarni o'rnating:
   ```bash
   pip install -r requirements.txt
   ```

3. `.env.example` dan `.env` faylini yarating:
   ```bash
   cp .env.example .env
   ```

4. `.env` faylida o'z ma'lumotlaringizni kiriting:
   - `BOT_TOKEN`: @BotFather dan olingan bot token
   - `DATABASE_URL`: PostgreSQL ulanish manzili
   - `ADMIN_IDS`: Admin foydalanuvchi ID lari (vergul bilan ajratilgan)
   - `BOT_USERNAME`: Bot username

5. PostgreSQL ma'lumotlar bazasini sozlang va `DATABASE_URL` ni yangilang

6. Ma'lumotlar bazasi migratsiyalarini ishga tushiring (Alembic ishlatilsa):
   ```bash
   alembic upgrade head
   ```

7. Botni ishga tushiring:
   ```bash
   python bot.py
   ```

## Project Structure

```
project/
├── bot.py                 # Main bot application
├── config.py             # Configuration management
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variables template
├── handlers/             # Telegram message handlers
│   ├── start.py
│   ├── tasks.py
│   ├── orders.py
│   ├── referral.py
│   ├── balance.py
│   ├── withdraw.py
│   └── admin.py
├── keyboards/            # Telegram keyboard layouts
│   ├── menu.py
│   └── admin_menu.py
├── database/             # Database layer
│   ├── db.py
│   ├── models.py
│   └── queries.py
├── utils/                # Utility functions
│   ├── subscription_checker.py
│   ├── reward_system.py
│   └── anti_cheat.py
└── services/             # Business logic services
    ├── task_service.py
    ├── order_service.py
    └── referral_service.py
```

## Database Schema

The bot uses PostgreSQL with the following main tables:
- `users`: User accounts and balances
- `tasks`: Subscription tasks for users
- `completed_tasks`: Task completion records
- `orders`: Subscriber purchase orders
- `transactions`: Financial transaction history
- `referrals`: Referral relationships
- `withdraw_requests`: Withdrawal requests

## Usage

1. Start the bot with `/start`
2. Users can earn money by completing subscription tasks
3. Channel owners can purchase subscribers
4. Use referral links to earn commissions
5. Claim daily bonuses
6. Request withdrawals when balance reaches minimum

## Admin Commands

- `/admin`: Access admin panel
- View statistics, manage withdraw requests, ban users, add balance

## Security Features

- Anti-cheat validation for subscriptions
- User banning system
- Balance verification
- Admin-only operations

## Contributing

1. Follow the existing code structure
2. Add proper error handling
3. Use async/await for all database operations
4. Test thoroughly before deploying

## License

This project is for educational purposes. Use responsibly and in compliance with Telegram's Terms of Service.