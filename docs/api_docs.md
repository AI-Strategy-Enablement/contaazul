App name: DEV-Michael-1772789359189  
Client-id: 5dtoe1iaupre93ml7tug7221vs  
Client-secret: 2b5ru9r12cum4usbckmu19ft1a7rvh3orq8f1opcaj4uoktk2uk  
—---  
Test account user: [cb09e788-6bd6-4599-b017-33b207d4fc98@devportal.com](mailto:cb09e788-6bd6-4599-b017-33b207d4fc98@devportal.com)  
Password: Ccb09e788-6bd6-4599-b017-33b207d4fc98   
—-  
Access token: eyJraWQiOiJUa1BRbWs0UlR3M3RuWlZXcDdEanBURFhcL2RTajNvMU5SckI0R3I3ZzFTMD0iLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIxNTZkOGIyNi00ZTJjLTRmZDYtOWE3OS1kM2Y2MjNhMTZjOTAiLCJkZXZpY2Vfa2V5Ijoic2EtZWFzdC0xX2RiNDZiMGJjLTViMWQtNDU5Ni1iMDhjLWNjNGE0ODM5OGFiNiIsImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC5zYS1lYXN0LTEuYW1hem9uYXdzLmNvbVwvc2EtZWFzdC0xX1ZwODNKMTF3QSIsImNsaWVudF9pZCI6IjVkdG9lMWlhdXByZTkzbWw3dHVnNzIyMXZzIiwib3JpZ2luX2p0aSI6IjViYTg1YmE3LTRjY2MtNDVjYi04OWYxLTJhMjFiMjc4YThiNSIsImV2ZW50X2lkIjoiMDM3NmJjMGQtZDM5My00MWQzLWJhNzctOWMzODMzYTgyNzgxIiwidG9rZW5fdXNlIjoiYWNjZXNzIiwic2NvcGUiOiJhd3MuY29nbml0by5zaWduaW4udXNlci5hZG1pbiIsImF1dGhfdGltZSI6MTc3Mjc4OTM3MSwiZXhwIjoxNzcyNzkyOTcxLCJpYXQiOjE3NzI3ODkzNzEsImp0aSI6ImI4MGQxODFhLWYzOWMtNGExNy04ZmU2LWYzOWQ2M2YzZDdiMSIsInVzZXJuYW1lIjoiY2IwOWU3ODgtNmJkNi00NTk5LWIwMTctMzNiMjA3ZDRmYzk4QGRldnBvcnRhbC5jb20ifQ.XNj0ObDYnpL4BGqbPKvHgaNQqmt4uS9fwLMAnKZasZAWchTuSlamDOKqCLQ25GURAJq-VBEsILF-eHCSWJ35FKSwuXnrH7iylXc\_nCM\_g\_50SNFLZevw1RncjSMuCPJuVtBJNFATXcIPLZcZCiF1GwonX\_idjmnzfTtV59vluKfFapXhTMAFSDGjZn\_X1EkigakCsQKZudX-fgJuABJawmCz2lJZKokw174ABis86VdgJY8VEFynYEX6ToRi43MCe4QG--hW\_tEtp8uyvxGc2SwP\_M6aiwq0e0hvTZUs-vjguue\_tt9aqAZhuzI1zP1DFunCbIlY7w9zuR4LyuM7Iw 

—----  
The **Access Token was successfully generated.** This access token is displayed only once on the screen and will be required to make API calls.  
**Attention\!**

Copy and store it in a safe place. If you lose this access token, you will need to generate a new one.

### **Important:**

* The **Access Token** will expire soon.  
* Start by testing your integration by searching for **financial categories.**

 curl \-i \-X GET 'https://api-v2.contaazul.com/v1/categorias' \-H 'Authorization: Bearer \<ACCESS\_TOKEN\_GERADO\>'

—--flow prompts—-

## **Testing authentication with OAuth 2.0**

---

### **The OAuth 2.0 authentication process involves three main steps:**

* [**Request an Authorization Code**](https://developers.contaazul.com/requestingcode) \- through the authorize endpoint, you will log in to Conta Azul using your ERP username and password.

* ### **URL to obtain the Authorization Code**

* Use the URL below to start the OAuth 2.0 flow with the parameters already configured for your application.  
* By accessing this URL:  
  * You will log in to Conta Azul.  
  * The system will be redirected to the configured **redirect\_uri** .  
  * The authorization code will be returned in the URL.  
  * This code is temporary (valid for 3 minutes) and must be exchanged for tokens in the next step.

* ### **ERP username and password**

* ### **User**

* ### **Password**

* [**Replace the Authorization Code with Tokens**](https://developers.contaazul.com/changecode) \- with the obtained code, your application must make a request to the token endpoint to receive the access\_token (used in API calls) and the refresh\_token (used to renew access).  
* [**Renewing the Access Token**](https://developers.contaazul.com/renewingaccesstoken) \- when the access\_token expires, simply use refresh\_token on the same token endpoint to obtain a new access token, without having to repeat the authorization process.

---

These steps ensure secure, seamless authentication that complies with the OAuth 2.0 standard.  
We are providing a **cURL example** so you can test the authentication process. **The URL defined** (https://contaazul.com) is used only for the **development application** , serving as support for testing during this stage.  
When you create your **production** application , you will need **to define your own redirect URL** , replacing the value shown in this example and following the steps described above.  
**Tip**

Run this test to ensure the authentication process is working correctly before integrating your application.

### **Authorization**

### **Example of cURL:**

With this example cURL, for the development application, you will only need to perform the Refresh Token step.  
 curl \--request POST \\  
        \--url https://auth.contaazul.com/oauth2/token \\  
        \--header 'Authorization: Basic NWR0b2UxaWF1cHJlOTNtbDd0dWc3MjIxdnM6MmI1cnU5cjEyY3VtNHVzYmNrbXUxOWZ0MWE3cnZoM29ycThmMW9wY2FqNHVva3RrMnVr' \\  
        \--header 'Content-Type: application/x-www-form-urlencoded' \\  
        \--data grant\_type=refresh\_token \\  
        \--data refresh\_token=REFRESH\_TOKEN\_GERADO

