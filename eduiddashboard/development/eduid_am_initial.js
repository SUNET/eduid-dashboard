/**
 * Created by lundberg on 2/11/14.
 */

// Bootstrap eduid_am with "mongo localhost:27017/eduid_am eduid_am_initial.js"

db.attributes.insert({
    "eduPersonPrincipalName" : "admin-admin",
    "mail" : "admin@example.com",
    "mailAliases" : [
        { "verified" : true,  "email" : "admin@example.com" }
    ],
    "eduPersonEntitlement" : [
		"urn:mace:eduid.se:role:admin"
	],
    "passwords" : [
        { "source" : "signup", "created_ts" : ISODate("2013-11-28T13:33:44.479Z"), "salt" : "$NDNv1H1$820c9041c9a5115eee9fa69e987651650d70e73778ccb450d19d2b5c8ca0b244$32$32$", 	"id" : "52974638afce772d92261077" }
    ]
});
db.attributes.insert({
    "eduPersonPrincipalName" : "helpdesk-helpdesk",
    "mail" : "helpdesk@example.com",
    "mailAliases" : [
        { "verified" : true,  "email" : "helpdesk@example.com" }
    ],
    "eduPersonEntitlement" : [
		"urn:mace:eduid.se:role:ra"
	],
    "passwords" : [
        { "source" : "signup", "created_ts" : ISODate("2013-11-28T13:33:44.479Z"), "salt" : "$NDNv1H1$820c9041c9a5115eee9fa69e987651650d70e73778ccb450d19d2b5c8ca0b244$32$32$", 	"id" : "52974638afce772d92261077" }
    ]
});
db.attributes.insert({
    "eduPersonPrincipalName" : "user1-user1",
    "mail" : "user1@example.com",
    "mailAliases" : [
        { "verified" : true,  "email" : "user1@example.com" }
    ],
    "passwords" : [
        { "source" : "signup", "created_ts" : ISODate("2013-11-28T13:33:44.479Z"), "salt" : "$NDNv1H1$820c9041c9a5115eee9fa69e987651650d70e73778ccb450d19d2b5c8ca0b244$32$32$", 	"id" : "52974638afce772d92261077" }
    ]
});
db.attributes.insert({
    "eduPersonPrincipalName" : "user2-user2",
    "mail" : "user2@example.com",
    "mailAliases" : [
        {  "verified" : true,  "email" : "user2@example.com" }
    ],
    "passwords" : [
        { "source" : "signup", "created_ts" : ISODate("2013-11-28T13:33:44.479Z"), "salt" : "$NDNv1H1$820c9041c9a5115eee9fa69e987651650d70e73778ccb450d19d2b5c8ca0b244$32$32$", 	"id" : "52974638afce772d92261077" }
    ]
});

