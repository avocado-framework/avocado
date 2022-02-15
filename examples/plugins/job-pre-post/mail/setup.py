from setuptools import setup

name = 'avocado_job_mail'
init_klass = 'MailInit'
klass = 'Mail'
entry_point = f'{name} = {name}:{klass}'
init_entry_point = f'{name} = {name}:{init_klass}'

if __name__ == '__main__':
    setup(name=name,
          version='1.0',
          description='Avocado Pre/Post Job Mail Notification',
          py_modules=[name],
          entry_points={
              'avocado.plugins.init': [init_entry_point],
              'avocado.plugins.job.prepost': [entry_point]
              }
          )
