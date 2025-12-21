![](https://github.com/thisisashwinraj/logiq-smart-appliance-management/blob/main/assets/readme_assets/logiq_banner_dark.png#gh-dark-mode-only)
![](https://github.com/thisisashwinraj/logiq-smart-appliance-management/blob/main/assets/readme_assets/logiq_banner_light.png#gh-light-mode-only)

<P align='justify'>Managing home appliances often involves juggling manuals, service calls and scattered records — a highly frustrating experience for many homeowners. With the rise of <B>Agentic AI</B> design framework, there's an opportunity to streamline and improve this process aptly through <B>intelligent systems</B> that can understand, guide, and act on behalf of the users</P>

<P align='justify'>This project showcases LogIQ, a smart home appliance management tool that offers an AI-powered application for customers and service engineers to manage household appliances and service bookings. The engineer application is designed to support field technicians with ticket management, navigation assistance, and AI-guided troubleshooting. The customer application enables the end-users to manage their registered appliances, log service requests, inquire about latest products, and access information related to appliance care and maintenance through an agentic interface</P>

> [!NOTE]
> Google AI Developer Programs team supported this work by providing Google Cloud Credit.


## Key Features

<P align='justify'>LogIQ brings together a wide set of capabilities for both customers and service engineers, designed to reduce friction at every stage of appliance maintenance. From intelligent ticket handling to AI-guided assistance, the system ensures faster resolutions, clearer communication, reduced operational cost and a simplified experience for everyone involved</P>

### Engineer Application

- **Manage Service Requests:** View all assigned tickets, check details, and accept or reject system-assigned requests
- **Route Preview and Optimization:** Shows the optimal route and order of visit from the engineer’s current location
- **Manage Ticket Activity:** Add or update notes to ticket activity, to maintain a clear record of all actions performed
- **Access Service History:** View any past service records to understand issues and resolution before starting the job
- **Reporting:** Verify onsite visit using customer-generated OTP verification and report any unsafe working condition
- **Manage Engineer Profile:** Edit & update engineer's personal details, specializations and other profile information

![](assets/screenshots/engineer_app/my_dashboard.png)
![](assets/screenshots/engineer_app/dashboard_service_request_details.png)
![](assets/screenshots/engineer_app/view_requests.png)

### Engineer Agent

- **account_management_agent**: Manages the engineer's profile, specializations, availability, and account workflows
- **navigation_agent**: Provides real-time route preview, weather updates, and traffic guidance to the service location
- **ticket_management_agent**: Fetches assigned requests, tracks activity, updates progress and handles past records
- **troubleshoot_agent**: Assists engineer with troubleshooting guidance, common ticket patterns, repair procedures

### Customer Application

- **Register Appliances:** Easily register new appliances with their model number, serial number, and purchase details
- **Raise Service Requests:** Log & manage service requests for registered appliances, to get onsite professional help
- **Manage Customer Profile**: Edit & update customer information, including contact details and service preferences
- **View Appliances Details:** Access centralized view of all registered appliances with warranty, specs, & support info
- **View Service Requests Status:** Track ongoing and past service requests, including live status and engineer details

![](assets/readme_assets/dashboard_1.png)
![](assets/readme_assets/dashboard_2.png)
![](assets/readme_assets/dashboard_3.png)

### Customer Agent

- **appliance_troubleshooting_agent:** Handles complex appliance issues, and offers usersafe troubleshooting advice
- **customer_appliances_agent**: Retrieves and summarizes information about all of customer’s registered appliances
- **product_enquiry_agent:** Answers question related to the latest appliance models, features, and recommendation
- **register_appliance_agent:** Guides the customers through the process of registering an appliance to their account
- **register_onsite_service_request_agent**: Facilitates the scheduling of appliance repair and onsite maintenance visit
- **service_requests_agent:** Fetches the status and history of the user’s service requests, including engineer's activity
- **update_customer_profile_agent:** Helps update customer's profile including their name, contact details & address


## Tech Stack

1. **Generative AI on Vertex AI**
    - **Google Gemini:** Used across AI agents for high-quality, low-latency responses, with function calling support
    - **Imagen 4:** Used to generate photo-realistic image catalog of fictional appliances, and other in-app graphics
    - **RAG Engine:** Supports various AI Agents by retrieving relevant answers from the corpus of support manuals
    - **Document AI Layout Parser:** Extracts structured content such as tables from manuals to build a RAG corpus

2. **Cloud Databases on GCP**
    - **Cloud SQL:** Stores structured data about appliances, customers, registered appliances, and engineer records
    - **Cloud Storage:** Stores graphics, invoices, warranty docs, manuals and attachments linked to service requests
    - **Firestore:** Manages realtime data for service requests, and stores appliance specifications in a NoSQL format

3. **Backend Infrastructure on GCP**
    - **Cloud Run:** Hosts the backend services responsible for automatically assigning engineers to service requests
    - **Google Auth Platform:** Provides secure user authentication and session management, using Google Oauth2
    - **Google Maps SDK:** Address auto-complete, validation, geocoding, and distance-based engineer assignment

4. **Frontend and Communication**
    - **Streamlit:** Python-based frontend with support for custom components, & CSS to enhance the user interface
    - **Twilio:** For delivering realtime SMS alert to users about service status updates, and engineer visit notification
    - **Brevo:** Sends automated transactional and notification emails—such as service confirmations, and reminders

![](assets/screenshots/gcp/cloud_sql_for_mysql.png)
![](assets/screenshots/gcp/cloud_storage.png)
![](assets/screenshots/gcp/firestore_appliance_specifications.png)


## Data Sources

The appliance dataset used in this project is **entirely synthetic** and was generated for demonstration purposes. Brand names, descriptions, and other technical specifications were **fabricated using Gemini 2.5** to simulate realistic product metadata across various categories such as refrigerators, washers & dryers, gas ranges and microwave ovens. Such an approach allowed for consistent & scalable data creation without relying on any **proprietary** or **sensitive information**.
 
To visually represent these products within the application, corresponding images were generated using **Imagen 4 on Vertex AI Studio**. These images were generated to closely match the appliance specifications created in the metadata.

## Retrieval-Augmented Generation (RAG) Workflows

For implementing **Retrieval-Augmented Generation (RAG)** workflow, publicly available service manuals were sourced and preprocessed. A service manual was linked to each sub-category to demonstrate **grounded** response generation. 

### For Customer Agent: 

Service Manuals were parsed using Google Cloud **DocumentAI Layout Parser** and the parsed corpus was indexed in a **RagManaged Vector Store** to enable the RAG engine to generate contextual responses for appliance troubleshooting

![](assets/screenshots/gcp/rag_engine_product_page.png)
![](assets/screenshots/gcp/rag_engine_service_manuals_corpus.png)

### For Engineer Agent:

**File Search tool** is used for enabling RAG workflow. The File Search tool imports, chunks, and indexes service manual data into **File Search Stores**, enabling fast retrieval of relevant information at runtime. All responses include **citations**.


## Setup and Installation

To run the streamlit application locally, clone the GitHub repository into your local system using the below command:

```bash
git clone https://github.com/thisisashwinraj/logiq-smart-appliance-management.git
```

Next, install the required dependencies using ```uv```. This command reads the ```pyproject.toml```  and installs the required dependencies into the virtual environment. On the first run, this command will create a managed virtual environment.

```bash
uv sync
```

If you're using the default virtual environment, you need to first activate this environment using the below command:

```bash
source .venv/bin/activate
```

Next, initialize the environment variables by renaming ```.env.example``` file to ```.env``` and update it with your own values:

```bash
cp .env.example .env
```

After this, setup the cloud SQL, cloud storage, and firestore databases as per the defined convention in the ```database``` folder. You may use the ```initialize_database``` script to create all databases with default configuration in a single click

![](assets/screenshots/gcp/iam_and_admin.png)

Next you need to create OAuth 2.0 credentials in the GCP Console. Start by navigating to the [OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent) in the Google Cloud Console. Click ```Get Started```, and provide the app information. For the ```audience```, choose **Internal** if you are using Google Workspace or **External** for a personal account and enter your contact information. Click ```Create```

After the OAuth consent screen is ready, select ```Clients``` from the left-hand menu and click on ```Create Client```. Select ```Web application``` as the **authentication type** and add ```http://localhost:8501/oauth2callback``` to **authorised redirect URIs**. Click ```Create```. Once done, retrieve ```client_id``` and ```client_secret``` from the console and update ```secrets.toml```.

![](assets/screenshots/gcp/oauth.png)

Once done, run the streamlit clients for the **customer** and **engineer** applications locally with the following commands:

```bash
streamlit run customer_app.py
streamlit run engineer_app.py
```


## Deploy to Cloud Run With Docker

To deploy your applications to **Cloud Run** using **Docker**, start by building the ```Docker image``` from the root directory:
```
docker build -t logiq-app .
```

Once the build completes, run the container locally to validate the deployment and ensure the service start correctly:
```
docker run -p 8501:8501 -e DEV_MODE=true logiq-app
```

After confirming that the application works as expected, tag the image with the appropriate **Container Registry** path:
```
docker tag logiq-app gcr.io/logiq-project/logiq-app
```

Next, push the tagged image to GCR and once the image is available in GCR, deploy both applications to **Cloud Run**:
```
docker push gcr.io/logiq-project/logiq-app
```

```
gcloud run deploy logiq-engineers
    --image gcr.io/logiq-project/logiq-app
    --platform managed
    --allow-unauthenticated
    --region us-central1
    --project logiq-project
```
```
gcloud run deploy logiq-customers
    --image gcr.io/logiq-project/logiq-app
    --platform managed
    --allow-unauthenticated
    --region us-central1
    --project logiq-project
    --set-env-vars APP_PATH=customer_app.py
```
![](assets/screenshots/gcp/cloud_run.png)


## Sample Agent Interactions

### Engineer Agent

![](assets/screenshots/chat/engineer_agent/chat_homepage.png)
![](assets/screenshots/chat/engineer_agent/pending_tickets_summary_chat.png)
![](assets/screenshots/chat/engineer_agent/ticket_details_chat.png)
![](assets/screenshots/chat/engineer_agent/troubleshoot_chat.png)

### Customer Agent

![](assets/readme_assets/product_enquiry_1.png)
![](assets/readme_assets/product_enquiry_2.png)
![](assets/readme_assets/product_enquiry_3.png)
![](assets/readme_assets/product_enquiry_4.png)

To view examples of multiturn conversations for agents in the customer support agent team check [assets/screenshots](https://github.com/thisisashwinraj/logiq-smart-appliance-management/tree/main/assets/screenshots/chat)


## Support and Feedback

Contributions are always welcome from the community. If you have any **queries** or would like to **share any feedback**, please drop a line at thisisashwinraj@gmail.com. You can also connect with me over [LinkedIn](https://www.linkedin.com/in/thisisashwinraj/) or [X (previously Twitter)](https://x.com/thisisashwinraj)
