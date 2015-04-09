#
# Copyright (c) 2015 NORDUnet A/S
# All rights reserved.
#
#   Redistribution and use in source and binary forms, with or
#   without modification, are permitted provided that the following
#   conditions are met:
#
#     1. Redistributions of source code must retain the above copyright
#        notice, this list of conditions and the following disclaimer.
#     2. Redistributions in binary form must reproduce the above
#        copyright notice, this list of conditions and the following
#        disclaimer in the documentation and/or other materials provided
#        with the distribution.
#     3. Neither the name of the NORDUnet nor the names of its
#        contributors may be used to endorse or promote products derived
#        from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#

__author__ = 'ft'

from eduid_userdb import UserDB, User
from eduiddashboard.user import DashboardUser
from eduiddashboard.user import DashboardLegacyUser as OldUser

import logging
logger = logging.getLogger('eduiddashboard')


class DashboardUserDB(UserDB):

    UserClass = DashboardUser

    def __init__(self, db_uri, collection='profiles'):
        super(DashboardUserDB, self).__init__(db_uri, collection=collection)

    def save(self, user, check_sync=True, old_format=True):
        # XXX old_format default is set to True here
        super(DashboardUserDB, self).save(user, check_sync=check_sync, old_format=old_format)


class DashboardOldUserDB(UserDB):

    UserClass = OldUser

    def __init__(self, db_uri, collection='profiles'):
        UserDB.__init__(self, db_uri, collection)


class UserDBWrapper(UserDB):

    UserClass = OldUser

    def get_user(self, email):
        # XXX remove logging
        logger.debug("GET USER {!r}".format(email))
        return self.get_user_by_mail(email)

    def get_user_by_oid(self, oid):
        # renamed method in UserDB
        return self.get_user_by_id(oid)

    def get_user_by_filter(self, filter, fields=None):
        """
        Locate a user in the userdb using a custom search filter.

        :param filter: the search filter
        :type filter: dict
        :param fields: the fields to return in the search result
        :type fields: dict
        :return: eduid_am.user.User
        :raise self.UserDoesNotExist: No user matching the search criteria
        :raise self.MultipleUsersReturned: More than one user matched the search criteria
        """
        logger.debug("Looking in {!r} using filter {!r}, returning fields {!r}".format(
            self._coll, filter, fields))
        users = self._get_users(filter, fields)

        if users.count() == 0:
            raise self.exceptions.UserDoesNotExist("No user found using filter")
        elif users.count() > 1:
            raise self.exceptions.MultipleUsersReturned("More than one user returned from filter query")

        logger.debug("Found user {!r}".format(users[0]))
        return self.UserClass(users[0])

    def _get_users(self, spec, fields=None):
        """
        Return a list with users object in the attribute manager MongoDB matching the filter

        :param spec: a standard mongodb read operation filter
        :param fields: If not None, pass as proyection to mongo searcher
        :return a list with users
        """
        if fields is None:
            return self._coll.find(spec)
        else:
            return self._coll.find(spec, fields)

    def exists_by_filter(self, spec):
        """
        Return true if at least one doc matchs with the value

        :param spec: The filter used in the query
        """

        docs = self._coll.find(spec)
        return docs.count() >= 1

    def exists_by_field(self, field, value):
        """
        Return true if at least one doc matchs with the value

        :param field: The name of a field
        :param value: The field value
        """

        return self.exists_by_filter({field: value})

    def save(self, user, check_sync=True, old_format=True):
        if isinstance(user, OldUser):
            user = User(data = user._mongo_doc)
        UserDB.save(self, user, check_sync, old_format)

    def get_identity_proofing(self, user):
        """
        Return the proofing urn value

        :param user: The user object
        :type user: OldUser
        """
        obj_id = user['_id']
        # TODO
        # This method need to be implemented
        al1_urn = 'http://www.swamid.se/policy/assurance/al1'
        al2_urn = 'http://www.swamid.se/policy/assurance/al2'
        user = self._coll.find_one({'_id': obj_id})
        if user is not None:
            nins = user.get('norEduPersonNIN')
            if nins is not None and len(nins) > 0:
                return al2_urn

        return al1_urn

