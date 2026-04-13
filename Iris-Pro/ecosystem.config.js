// PM2 process manager config for IRIS
// Usage:
//   First time:  pm2 start ecosystem.config.js && pm2 save && pm2 startup
//   Restart:     pm2 restart iris
//   Stop:        pm2 stop iris
//   Logs:        pm2 logs

module.exports = {
  apps: [
    {
      name: "iris-dashboard",
      script: "python3",
      args: "dashboard/app.py",
      cwd: __dirname,
      watch: false,
      autorestart: true,
      restart_delay: 3000,
      max_restarts: 20,
      env_file: ".env",
      log_file: "logs/pm2-dashboard.log",
      error_file: "logs/pm2-dashboard-error.log",
      time: true,
    },
    {
      name: "iris-telegram",
      script: "python3",
      args: ".claude/skills/telegram/scripts/telegram_handler.py",
      cwd: __dirname,
      watch: false,
      autorestart: true,
      restart_delay: 5000,
      max_restarts: 20,
      env_file: ".env",
      log_file: "logs/pm2-telegram.log",
      error_file: "logs/pm2-telegram-error.log",
      time: true,
      // Only start if token is configured — checked at runtime by the script itself
    },
  ],
};
