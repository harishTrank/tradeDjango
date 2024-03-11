module.exports = {
    name: 'django-app',
    script: 'manage.py',
    args: ['runserver', '0.0.0.0:8000'],
    interpreter: 'python3',
    exec_mode: 'fork',
    instances: 1,
    watch: true,
    max_memory_restart: "1G",
  };