module.exports = {
  apps: [
    {
      name: "njob-automation",
      script: "njob_login.py",
      interpreter: "python",
      watch: false,
      autorestart: true,
      env: {
        NODE_ENV: "production",
      },
    },
  ],
};
