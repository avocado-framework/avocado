import os

from avocado import Test, fail_on
from avocado.utils import archive, build, process


class Hello(Test):

    def setUp(self):
        tarball_locations = [
            'https://mirrors.peers.community/mirrors/gnu/hello/hello-2.9.tar.gz',
            'https://mirrors.kernel.org/gnu/hello/hello-2.9.tar.gz',
            'http://gnu.c3sl.ufpr.br/ftp/hello-2.9.tar.gz',
            'ftp://ftp.funet.fi/pub/gnu/prep/hello/hello-2.9.tar.gz'
            ]
        self.hello = self.fetch_asset(
            name='hello-2.9.tar.gz',
            asset_hash='cb0470b0e8f4f7768338f5c5cfe1688c90fbbc74',
            locations=tarball_locations)

        sig_locations = [
            'https://mirrors.peers.community/mirrors/gnu/hello/hello-2.9.tar.gz.sig',
            'https://mirrors.kernel.org/gnu/hello/hello-2.9.tar.gz.sig',
            'http://gnu.c3sl.ufpr.br/ftp/hello-2.9.tar.gz.sig',
            'ftp://ftp.funet.fi/pub/gnu/prep/hello/hello-2.9.tar.gz.sig'
            ]
        self.hello_sig = self.fetch_asset(
            name='hello-2.9.tar.gz.sig',
            asset_hash='f3b9fae20c35740004ae7b8de1301836dab4ac30',
            locations=sig_locations)

    @fail_on(process.CmdError)
    def test_gpg_signature(self):
        keyring = os.path.join(self.workdir, "tempring.gpg")
        gpg_cmd = f"gpg --no-default-keyring --keyring {keyring}"
        signer_pubkey = self.get_data("gnu_hello_signer.gpg")
        import_cmd = f"{gpg_cmd} --import {signer_pubkey}"
        # gpg will not return 0 when creating a new keyring and
        # importing the public key
        process.run(import_cmd, ignore_status=True)
        verify_cmd = f"{gpg_cmd} --verify {self.hello_sig} {self.hello}"
        process.run(verify_cmd)

    @fail_on(process.CmdError)
    def test_build_run(self):
        hello_src = os.path.join(self.workdir, 'hello-2.9')
        archive.uncompress(self.hello, self.workdir)
        build.configure(hello_src)
        build.make(hello_src)
        process.run(os.path.join(hello_src, 'src', 'hello'))
