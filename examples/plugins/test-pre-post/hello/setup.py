from setuptools import setup

if __name__ == "__main__":
    setup(
        name="avocado-hello-world-pre-post-test",
        version="1.0",
        description="Avocado Hello World pre and post test plugin",
        py_modules=["hello"],
        entry_points={
            "avocado.plugins.test.pre": ["hello_pre = hello:HelloWorld"],
            "avocado.plugins.test.post": ["hello_post = hello:HelloWorld"],
        },
    )
