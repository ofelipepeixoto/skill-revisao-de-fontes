"""Adapter bibliográfico restrito. Metadados nunca aprovam alegações.

Implementação original; fronteiras inspiradas no verificador MIT de K-Dense
scientific-agent-skills, revisão a1043ef544e3a100c28e70a736b6cf32554d0677.
Sem provider pago, token, coleta de URLs arbitrárias ou integração automática.
"""
import json
import re
from urllib.parse import quote, urlsplit
from urllib.request import HTTPSHandler, HTTPRedirectHandler, ProxyHandler, Request, build_opener
from urllib.error import HTTPError, URLError

MAX_BYTES = 65536
TIMEOUT = 5
HOST_PATHS = {'doi.org': '/api/handles/', 'api.crossref.org': '/works/'}

def normalizar_doi(value):
    if not isinstance(value, str) or len(value) > 256:
        raise ValueError('DOI inválido')
    value = value.strip().lower()
    if not re.fullmatch(r'10\.\d{4,9}/[a-z0-9._;()/:+-]{1,200}', value):
        raise ValueError('informe DOI simples, sem URL, percent-encoding, query ou fragmento')
    return value

def endpoint(host, doi):
    if host not in HOST_PATHS:
        raise ValueError('destino não permitido')
    return 'https://' + host + HOST_PATHS[host] + quote(normalizar_doi(doi), safe='')

class SemRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def consultar_http(url):
    """Leitura opt-in de endpoint exato, sem proxies de ambiente ou redirects.

    Duas chamadas no máximo por consulta DOI; nenhuma repetição automática.
    Este transporte não é invocado pelos testes nem por CLI automática.
    """
    parsed = urlsplit(url)
    prefix = HOST_PATHS.get(parsed.hostname)
    if (parsed.scheme != 'https' or not prefix or parsed.netloc != parsed.hostname
            or not parsed.path.startswith(prefix) or parsed.query or parsed.fragment):
        raise ValueError('destino não permitido')
    # The only accepted URL is exactly one constructed from the strict DOI.
    from urllib.parse import unquote
    doi = normalizar_doi(unquote(parsed.path[len(prefix):]))
    if url != endpoint(parsed.hostname, doi):
        raise ValueError('endpoint não canônico')
    request = Request(url, headers={'Accept': 'application/json',
                                   'User-Agent': 'RadarBibliografiaFixturePilot/0.1'})
    opener = build_opener(ProxyHandler({}), HTTPSHandler(), SemRedirect())
    try:
        with opener.open(request, timeout=TIMEOUT) as response:
            data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise ValueError('resposta excede limite')
            return response.status, json.loads(data)
    except HTTPError as exc:
        # Do not echo remote bodies, redirect targets or user inputs to logs.
        status = exc.code
        exc.close()
        return status, None

def consultar_doi(doi, transporte):
    """Transport must return (HTTP status, parsed JSON). No default network call."""
    doi = normalizar_doi(doi)
    result = {'doi': doi, 'registro': 'inconclusivo', 'metadados': 'indisponiveis',
              'suporte_alegacao': 'nao_avaliado', 'revisao_humana': 'pendente'}
    try:
        status, data = transporte(endpoint('doi.org', doi))
        if (type(status) is not int or not isinstance(data, dict)
                or type(data.get('responseCode')) is not int
                or not isinstance(data.get('handle'), str) or data['handle'].lower() != doi):
            return result
        if status in (200, 404) and data.get('responseCode') == 100:
            result['registro'] = 'ausente'
            return result
        if status != 200 or data.get('responseCode') != 1:
            return result
        result['registro'] = 'registrado'
        status, data = transporte(endpoint('api.crossref.org', doi))
        message = data.get('message') if isinstance(data, dict) else None
        if (type(status) is int and status == 200 and isinstance(message, dict)
                and isinstance(message.get('DOI'), str) and message['DOI'].lower() == doi):
            result['metadados'] = 'obtidos'
            title = message.get('title')
            if isinstance(title, list) and title and isinstance(title[0], str):
                result['titulo'] = title[0][:1000]
    except (OSError, ValueError, TypeError, AttributeError, RecursionError, URLError):
        # Transport uncertainty never becomes absence or factual approval.
        pass
    return result
