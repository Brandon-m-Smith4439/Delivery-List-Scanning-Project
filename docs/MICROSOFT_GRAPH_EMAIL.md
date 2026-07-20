# Microsoft Graph Email Setup

This release can send the existing customer manifests, ready notices, and Admin test messages through Microsoft Graph.

Configured sender:

- `BarefootNC.Glass@bldr.com`

Default test recipient:

- `brandon.m.smith@bldr.com`

The application uses one existing outbox and one existing Admin test form. Graph replaces only the delivery transport; it does not create a second email workflow.

## What is already implemented

- App-only Microsoft Graph `sendMail` support.
- Local Windows authentication with an Entra app registration and client secret.
- The local client secret is stored with Windows DPAPI encryption, tied to the Windows account that ran setup.
- Azure App Service authentication with system-assigned or user-assigned managed identity.
- In-memory access-token caching and one authorization retry.
- Sending as `BarefootNC.Glass@bldr.com` through `/users/{sender}/sendMail`.
- Messages saved to the sender's Sent Items by default.
- Existing SMTP support retained as a fallback.
- Existing draft behavior retained when neither Graph nor SMTP is configured.

## Step 1: Have BLDR IT create the application identity

The preferred registration name is:

`Barefoot Delivery Scanner Email`

IT needs to provide these non-secret values:

- Microsoft Entra tenant ID.
- Application/client ID.

For the local Windows test, IT also creates a client secret and gives the secret value to the person performing setup. Do not place that secret in email, documentation, source code, or chat.

For a quick controlled test, an Entra administrator can grant the app the Microsoft Graph **Mail.Send application permission** and grant tenant admin consent. This is organization-wide unless Exchange access is separately constrained.

For the preferred least-privilege production setup, Exchange Online RBAC for Applications should grant **Application Mail.Send** only to a mailbox scope containing `BarefootNC.Glass@bldr.com`. Microsoft documents Exchange Application RBAC as the replacement for new Application Access Policies.

### Preferred Exchange Online RBAC outline for IT

1. Create a mail-enabled security group that contains only `BarefootNC.Glass@bldr.com`.
2. Register the Entra service principal pointer in Exchange Online.
3. Create an Exchange management scope based on that group's distinguished name.
4. Assign the `Application Mail.Send` role to the app within that scope.
5. Test the service principal authorization against `BarefootNC.Glass@bldr.com` and against another mailbox that should be out of scope.

Example outline for an Exchange administrator; replace every placeholder with values from the tenant:

```powershell
Connect-ExchangeOnline

$AppId = "<application-client-id>"
$EnterpriseAppObjectId = "<enterprise-application-service-principal-object-id>"
$ScopeGroup = Get-DistributionGroup "Barefoot Delivery Scanner Mailboxes"

New-ServicePrincipal `
    -AppId $AppId `
    -ObjectId $EnterpriseAppObjectId `
    -DisplayName "Barefoot Delivery Scanner Email"

New-ManagementScope `
    -Name "Barefoot Delivery Scanner Mailbox Scope" `
    -RecipientRestrictionFilter "MemberOfGroup -eq '$($ScopeGroup.DistinguishedName)'"

New-ManagementRoleAssignment `
    -Name "Barefoot Delivery Scanner Mail.Send" `
    -App $EnterpriseAppObjectId `
    -Role "Application Mail.Send" `
    -CustomResourceScope "Barefoot Delivery Scanner Mailbox Scope"

Test-ServicePrincipalAuthorization `
    -Identity $EnterpriseAppObjectId `
    -Resource "BarefootNC.Glass@bldr.com"
```

Important: Exchange RBAC and Microsoft Entra application-permission grants are additive. If IT wants strict mailbox scoping through Exchange RBAC, it should not leave an unscoped organization-wide `Mail.Send` application grant in Entra for the same app.

## Step 2: Configure the local Windows scanner

After IT provides the tenant ID, client ID, and client-secret value:

1. Stop the Delivery List Scanner.
2. Double-click `Configure-MicrosoftGraphEmail.bat`.
3. Enter the tenant ID.
4. Enter the application/client ID.
5. Accept or change the sender mailbox.
6. Accept or change the test recipient.
7. Paste the client secret into the hidden secure prompt.
8. Start the scanner with `Start-DeliveryScannerWebApp.bat`.

The utility creates:

`data\secrets\microsoft-graph-email.json`

The client secret in that file is encrypted with Windows DPAPI for the Windows account that ran the setup utility. The launcher decrypts it only in memory and passes it to the Python process. A different Windows account normally cannot decrypt it; rerun setup under the account that runs the scanner.

Never copy the generated secret file into a release ZIP, source repository, email, or shared folder. It should remain with the local protected `data` folder.

## Step 3: Send the controlled test

1. Sign in to the scanner as an Admin.
2. Open **Admin**.
3. Open the customer-email configuration.
4. Confirm the status shows **Microsoft Graph live**.
5. Confirm the sender is `BarefootNC.Glass@bldr.com`.
6. Confirm the test recipient is `brandon.m.smith@bldr.com`.
7. Use **Send Test Email**.
8. Confirm the test appears in the Admin outbox as Sent.
9. Confirm the message arrives at `brandon.m.smith@bldr.com`.
10. Confirm a copy appears in the Barefoot mailbox Sent Items.

If the test fails, the full Microsoft response is stored in the outbox error field without exposing the access token or client secret.

## Common test failures

- `AADSTS7000215` or invalid client secret: the secret value is wrong, expired, or the secret ID was entered instead of the secret value.
- `AADSTS700016`: tenant ID or client ID is incorrect, or the app registration is in another tenant.
- HTTP 403 / access denied: admin consent or Exchange RBAC assignment is missing, has not propagated, or the sender is outside the assigned scope.
- Mailbox not found: `BarefootNC.Glass@bldr.com` is not a valid Exchange Online mailbox/user principal in the tenant.
- Setup decrypt error: the scanner is running under a different Windows account; rerun the setup utility as the account that starts the scanner.

Microsoft notes that Exchange Application RBAC permission changes can take time to propagate, even when the authorization test cmdlet already reports the expected scope.

## Azure App Service later

The same Graph sender switches to managed identity in Azure:

```text
DLS_EMAIL_TRANSPORT=graph
DLS_GRAPH_AUTH_MODE=managed-identity
DLS_GRAPH_SENDER=BarefootNC.Glass@bldr.com
DLS_EMAIL_TEST_RECIPIENT=brandon.m.smith@bldr.com
DLS_GRAPH_SAVE_TO_SENT_ITEMS=1
```

The App Service managed identity must receive the Graph/Exchange `Application Mail.Send` permission scoped to the Barefoot mailbox. No client secret is used in Azure. The application requests a Graph token through the App Service `IDENTITY_ENDPOINT` and `IDENTITY_HEADER` supplied by Azure.

## Security rules

- Do not paste the client secret into chat.
- Do not write the secret in the BAT, PS1, Python, JSON delivery-list files, or changelog.
- Do not commit `data\secrets` to Git.
- Use the shortest practical client-secret expiration for local testing and rotate it before expiration.
- Prefer the Azure managed-identity setup for production hosting.
- Restrict application sending to the Barefoot mailbox through Exchange Online RBAC where BLDR policy permits it.
