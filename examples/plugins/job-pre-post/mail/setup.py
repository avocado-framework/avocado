from setuptools import setup

name = 'avocado_job_mail'
klass = 'Mail'
entry_point = '%s = %s:%s' % ('job_mail', name, klass)

if __name__ == '__main__':
    setup(name=name,
          version='1.0',
          description='Avocado Pre/Post Job Mail Notification',
          py_modules=[name],
          entry_points={
              'avocado.plugins.job.prepost': [
                  'mail = avocado_job_mail:Mail',
              ],
              'avocado.plugins.cli': [
                  'job_mail = avocado_job_mail:MailCLI'
              ]
          }
    )
