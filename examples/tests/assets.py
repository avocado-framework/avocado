import os

from avocado import Test, fail_on
from avocado.utils import archive, build, process


class Hello(Test):

    def setUp(self):
        mirrors = ['https://mirrors.peers.community/mirrors/gnu/hello/',
                   'https://mirrors.kernel.org/gnu/hello/',
                   'http://gnu.c3sl.ufpr.br/ftp/',
                   'ftp://ftp.funet.fi/pub/gnu/prep/hello/']
        hello = 'hello-2.9.tar.gz'
        hello_locations = ["%s%s" % (loc, hello) for loc in mirrors]
        hello_sig = 'hello-2.9.tar.gz.sig'
        hello_sig_locations = ["%s%s" % (loc, hello_sig) for loc in mirrors]
        self.hello = self.fetch_asset(
            name=hello,
            locations=hello_locations,
            asset_hash='cb0470b0e8f4f7768338f5c5cfe1688c90fbbc74')
        self.hello_sig = self.fetch_asset(
            name=hello_sig,
            asset_hash='f3b9fae20c35740004ae7b8de1301836dab4ac30',
            locations=hello_sig_locations)

    @fail_on(process.CmdError)
    def test_gpg_signature(self):
        keyring = os.path.join(self.workdir, "tempring.gpg")
        gpg_cmd = "gpg --no-default-keyring --keyring %s" % keyring
        signer_pubkey = self.get_data("gnu_hello_signer.gpg")
        import_cmd = "%s --import %s" % (gpg_cmd, signer_pubkey)
        # gpg will not return 0 when creating a new keyring and
        # importing the public key
        process.run(import_cmd, ignore_status=True)
        verify_cmd = "%s --verify %s %s" % (gpg_cmd,
                                            self.hello_sig,
                                            self.hello)
        process.run(verify_cmd)

    @fail_on(process.CmdError)
    def test_build_run(self):
        hello_src = os.path.join(self.workdir, 'hello-2.9')
        archive.uncompress(self.hello, self.workdir)
        build.configure(hello_src)
        build.make(hello_src)
        process.run(os.path.join(hello_src, 'src', 'hello'))
