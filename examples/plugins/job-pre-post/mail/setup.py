from setuptools import setup

name = 'avocado_job_mail'
klass = 'Mail'
entry_point = '%s = %s:%s' % (name, name, klass)

if __name__ == '__main__':
    setup(name=name,
          version='1.0',
          description='Avocado Pre/Post Job Mail Notification',
          py_modules=[name],
          entry_points={
              'avocado.plugins.job.prepost': [entry_point]
              }
          )
