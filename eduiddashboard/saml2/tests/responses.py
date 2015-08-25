# Copyright (C) 2011-2012 Yaco Sistemas (http://www.yaco.es)
# Copyright (C) 2010 Lorenzo Gil Sanchez <lorenzo.gil.sanchez@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#            http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime


def auth_response(session_id, uid):
    """Generates a fresh signed authentication response"""
    timestamp = datetime.datetime.now() - datetime.timedelta(seconds=10)
    tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)

    sp_baseurl = 'http://eduid.example.com:6544/'


    saml_response_tpl = """<?xml version='1.0' encoding='UTF-8'?>
<samlp:Response xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
                xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                Destination="{sp_url}saml2/acs/"
                ID="id-88b9f586a2a3a639f9327485cc37c40a"
                InResponseTo="{session_id}"
                IssueInstant="{timestamp}"
                Version="2.0">
    <saml:Issuer Format="urn:oasis:names:tc:SAML:2.0:nameid-format:entity">
        https://idp.example.com/simplesaml/saml2/idp/metadata.php
    </saml:Issuer>
    <samlp:Status>
        <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success" />
    </samlp:Status>
    <saml:Assertion ID="id-093952102ceb73436e49cb91c58b0578"
                    IssueInstant="{timestamp}"
                    Version="2.0">
        <saml:Issuer Format="urn:oasis:names:tc:SAML:2.0:nameid-format:entity">
            https://idp.example.com/simplesaml/saml2/idp/metadata.php
        </saml:Issuer>
        <saml:Subject>
            <saml:NameID Format="urn:oasis:names:tc:SAML:2.0:nameid-format:transient"
                    NameQualifier=""
                    SPNameQualifier="{sp_url}saml2/metadata/">
                1f87035b4c1325b296a53d92097e6b3fa36d7e30ee82e3fcb0680d60243c1f03
            </saml:NameID>
            <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
                <saml:SubjectConfirmationData InResponseTo="{session_id}"
                                              NotOnOrAfter="{tomorrow}"
                                              Recipient="{sp_url}saml2/acs/" />
            </saml:SubjectConfirmation>
        </saml:Subject>
        <saml:Conditions NotBefore="{yesterday}"
                         NotOnOrAfter="{tomorrow}">
            <saml:AudienceRestriction>
                <saml:Audience>{sp_url}saml2/metadata/</saml:Audience>
            </saml:AudienceRestriction>
        </saml:Conditions>
        <saml:AuthnStatement AuthnInstant="{timestamp}"
                             SessionIndex="{session_id}">
            <saml:AuthnContext>
                <saml:AuthnContextClassRef>
                    urn:oasis:names:tc:SAML:2.0:ac:classes:Password
                </saml:AuthnContextClassRef>
            </saml:AuthnContext>
        </saml:AuthnStatement>

        <saml:AttributeStatement>
            <saml:Attribute FriendlyName="uid" Name="urn:oid:0.9.2342.19200300.100.1.1" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:uri">
                <saml:AttributeValue xsi:nil="true" xsi:type="xs:string">{uid}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:uri"
                            Name="urn:oid:0.9.2342.19200300.100.1.3"
                            FriendlyName="mail">
                <saml:AttributeValue xsi:nil="true" xsi:type="xs:string">{uid}</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:uri"
                            Name="urn:oid:1.3.6.1.4.1.5923.1.1.1.6"
                            FriendlyName="eduPersonPrincipalName">
                <saml:AttributeValue xsi:nil="true" xsi:type="xs:string">{uid}</saml:AttributeValue>
            </saml:Attribute>
        </saml:AttributeStatement>
    </saml:Assertion>
</samlp:Response>"""

    return saml_response_tpl.format(**{
        'uid': uid,
        'session_id': session_id,
        'timestamp': timestamp.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'tomorrow': tomorrow.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'yesterday': yesterday.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'sp_url': sp_baseurl,
    })


def logout_response(session_id):
    timestamp = datetime.datetime.now() - datetime.timedelta(seconds=10)

    saml_logout_response = """
<samlp:LogoutResponse xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                      xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
                      ID="_57c8021aeb90bbf93d5a587f5c9c68cccfe42d95f6"
                      Version="2.0"
                      IssueInstant="{now}"
                      Destination="http://eduid.example.com:6544/saml2/ls/"
                      InResponseTo="{session_id}"
                      >
    <saml:Issuer>https://idp.example.com/simplesaml/saml2/idp/metadata.php</saml:Issuer>
    <samlp:Status>
        <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success" />
    </samlp:Status>
</samlp:LogoutResponse>""".format(
        now=timestamp.strftime('%Y-%m-%dT%H:%M:%SZ'),
        session_id=session_id
    )

    return saml_logout_response


def logout_request(session_id, idp=None):
    timestamp = datetime.datetime.now() - datetime.timedelta(seconds=10)
    if idp is None:
        idp = 'https://idp.example.com/simplesaml/saml2/idp/metadata.php'
    saml_logout_request = """
<samlp:LogoutRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                     xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
                     ID="{session_id}"
                     Version="2.0"
                     IssueInstant="{now}"
                     Destination="http://eduid.example.com:6544/saml2/ls/"
                     >
    <saml:Issuer>{idp}</saml:Issuer>
    <saml:NameID SPNameQualifier="http://eduid.example.com:6544/saml2/metadata/"
                 Format="urn:oasis:names:tc:SAML:2.0:nameid-format:transient"
                 >{session_id}</saml:NameID>
    <samlp:SessionIndex>{session_id}</samlp:SessionIndex>
</samlp:LogoutRequest>""".format(
        now=timestamp.strftime('%Y-%m-%dT%H:%M:%SZ'),
        session_id=session_id,
        idp=idp
    )
    return saml_logout_request
