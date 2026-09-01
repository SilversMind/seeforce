from c4parser.static_facts import noise


def test_top_level_name_python_dotted():
    assert noise.top_level_name("apps.subscriptions.manager", "python") == "apps"


def test_top_level_name_typescript_relative():
    assert noise.top_level_name("./util", "typescript") == "./util"


def test_top_level_name_typescript_bare():
    assert noise.top_level_name("axios/lib/foo", "typescript") == "axios"


def test_top_level_name_typescript_scoped():
    assert noise.top_level_name("@aws-sdk/client-s3", "typescript") == "@aws-sdk/client-s3"


def test_is_known_external_python():
    assert noise.is_known_external("stripe", "python") is True
    assert noise.is_known_external("some_random_lib", "python") is False


def test_is_known_external_typescript():
    assert noise.is_known_external("axios", "typescript") is True
    assert noise.is_known_external("lodash", "typescript") is False
