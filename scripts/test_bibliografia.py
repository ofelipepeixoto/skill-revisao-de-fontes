import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

spec = importlib.util.spec_from_file_location('bibliografia', Path(__file__).with_name('bibliografia.py'))
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
DOI = '10.1000/fixture'

class BibliografiaTests(unittest.TestCase):
    def test_registered_is_not_approval(self):
        transport = Mock(side_effect=[(200, {'handle':DOI,'responseCode':1}),
                                     (200, {'message':{'DOI':DOI,'title':['Fixture']}})])
        result = b.consultar_doi(DOI, transport)
        self.assertEqual(result['registro'], 'registrado')
        self.assertEqual(result['metadados'], 'obtidos')
        self.assertEqual(result['suporte_alegacao'], 'nao_avaliado')
        self.assertEqual(result['revisao_humana'], 'pendente')
        self.assertEqual(transport.call_count, 2)
        self.assertEqual(transport.call_args.args[0], b.endpoint('api.crossref.org', DOI))

    def test_missing_requires_identity(self):
        for status, data, expected in [(404, {'handle':DOI,'responseCode':100},'ausente'),
                                      (404, {},'inconclusivo'),
                                      (200, {'handle':'10.1000/other','responseCode':100},'inconclusivo'),
                                      (403, {'handle':DOI,'responseCode':100},'inconclusivo')]:
            with self.subTest(status=status,data=data):
                self.assertEqual(b.consultar_doi(DOI, Mock(return_value=(status,data)))['registro'],expected)

    def test_inconclusive_failures_no_retries(self):
        for response in [(302,None),(429,None),(500,None),(200,[]),(200,{'handle':None}),TimeoutError()]:
            transport = Mock(side_effect=response if isinstance(response,Exception) else None,
                             return_value=response)
            self.assertEqual(b.consultar_doi(DOI, transport)['registro'],'inconclusivo')
            self.assertEqual(transport.call_count,1)

    def test_crossref_failure_does_not_erase_registration(self):
        for response in [(404,None),(200,{'message':{'DOI':'10.1000/other'}}),TimeoutError()]:
            transport = Mock(side_effect=[(200,{'handle':DOI,'responseCode':1}),response])
            result = b.consultar_doi(DOI,transport)
            self.assertEqual(result['registro'],'registrado')
            self.assertEqual(result['metadados'],'indisponiveis')

    def test_malformed_codes_are_inconclusive(self):
        for code in [True, False, '1', None, [], {}]:
            transport=Mock(return_value=(200,{'handle':DOI,'responseCode':code}))
            self.assertEqual(b.consultar_doi(DOI,transport)['registro'],'inconclusivo')
            self.assertEqual(transport.call_count,1)

    def test_refuse_arbitrary_identifiers(self):
        for value in ['https://doi.org/10.1000/x','10.1000/x?redirect=localhost',
                      '10.1000/x#frag','10.1000/%2f','10.1000/\n','http://127.0.0.1/',None,'x'*300]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                b.consultar_doi(value,Mock())

    def test_http_destination_checks_before_transport(self):
        with patch.object(b,'build_opener') as opener:
            for url in ['http://doi.org/api/handles/10.1000%2Fx','https://localhost/a',
                        'https://doi.org.evil.invalid/a','https://doi.org:443/api/handles/10.1000%2Fx',
                        'https://user@doi.org/api/handles/10.1000%2Fx',
                        'https://api.crossref.org/works/10.1000%2Fx?x=1',
                        'https://doi.org/api/handles/../x']:
                with self.subTest(url=url),self.assertRaises(ValueError):
                    b.consultar_http(url)
            opener.assert_not_called()

    def test_http_bounds_and_no_redirect_policy(self):
        response = Mock(status=200)
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value=b'{}'
        opener=Mock()
        opener.open.return_value=response
        with patch.object(b,'build_opener',return_value=opener) as build:
            self.assertEqual(b.consultar_http(b.endpoint('doi.org',DOI)),(200,{}))
            self.assertEqual(opener.open.call_args.kwargs['timeout'],5)
            response.read.assert_called_with(b.MAX_BYTES+1)
            self.assertTrue(any(isinstance(x,b.SemRedirect) for x in build.call_args.args))
            response.read.return_value=b'x'*(b.MAX_BYTES+1)
            with self.assertRaises(ValueError): b.consultar_http(b.endpoint('doi.org',DOI))
        self.assertIsNone(b.SemRedirect().redirect_request(None,None,302,'',{},'http://127.0.0.1'))

    def test_redirect_response_is_not_followed(self):
        opener=Mock()
        opener.open.side_effect=HTTPError('synthetic',302,'redirect',{},None)
        with patch.object(b,'build_opener',return_value=opener):
            self.assertEqual(b.consultar_http(b.endpoint('doi.org',DOI)),(302,None))
        self.assertEqual(opener.open.call_count,1)

if __name__=='__main__': unittest.main()
