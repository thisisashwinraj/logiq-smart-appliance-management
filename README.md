# LogIQ: Smart Appliance Management

Managing home appliances often involves juggling manuals, service calls and scattered records — a highly frustrating experience for many homeowners. With the rise of Agentic AI design framework, there's an opportunity to streamline and improve this process aptly through intelligent systems that can understand, guide, and act on behalf of the users.

This project showcases LogIQ - a fictional home appliance manufacturer that offers an AI-powered application to help customers seamlessly manage their household devices. At the core of the app is a smart assistant—an  AI chatbot that helps users manage their registered appliances, raise service requests, and look up information about appliance care and maintenance. The chatbot integrates seamlessly with the app, allowing users to interact with its features manually through the interface or switch to **AI mode** for a guided, chat-based experience. Watch the Customer App demo [here](https://github.com/thisisashwinraj/LogIQ-Smart-Appliance-Management/tree/main?tab=readme-ov-file#demo)

## Customer App Features

The web app is a **smart home appliance management platform** designed to streamline and enhance how customers interact with their household devices. The app provides a clean, intuitive interface and several key features that make appliance ownership & support effortless. Some of the key aspects of the customer application are as described here:

- **Register Appliances:** Easily register new household appliances with model, serial number, and purchase details
- **Raise Service Requests:** Log & manage service requests for registered appliances, to get onsite professional help
- **View Appliances Details:** Access centralized view of all registered appliances with warranty, specs & support info
- **View Service Requests Status:** Track ongoing and past service requests, including live status & engineer details
- **Manage Customer Profile:** Edit & update customer information, including contact details and service preferences

![](https://github.com/thisisashwinraj/LogIQ-Smart-Appliance-Management/blob/main/assets/screenshots/logiq_home_1.PNG)

## Customer Agent Features

LogIQ's customer agent is a multi-agent system designed to streamline home appliance management and customer support. It use **Google Agent Development Kit (ADK)** to enable intelligent context-aware interactions across agents. These agents then collaborate to interpret the input query, retrieve relevant data, and deliver task specific responses.

- **appliance_troubleshooting_agent:** Handles complex appliance issues, and offers usersafe troubleshooting advice
- **customer_appliances_agent**: Retrieves and summarizes information about all of customer’s registered appliances
- **product_enquiry_agent:** Answers question related to the latest appliance models, features, and recommendation
- **register_appliance_agent:** Guides the customers through the process of registering an appliance to their account
- **register_onsite_service_request_agent**: Facilitates the scheduling of appliance repair and onsite maintenance visit
- **service_requests_agent:** Fetches the status and history of the user’s service requests, including engineer's activity
- **update_customer_profile_agent:** Helps update customer's profile including their name, contact details & address

![](https://github.com/thisisashwinraj/LogIQ-Smart-Appliance-Management/blob/main/assets/screenshots/chat/appliance_troubleshooting/chat_appliance_troubleshooting_1.PNG)

## Tech Stack

1. **Generative AI on Vertex AI**
    - **Gemini 2.5 Pro:** Used across AI agents for high-quality, low-latency responses, with function calling support
    - **Imagen 4:** Used to generate photo-realistic image catalog of fictional appliances, and other in-app graphics
    - **RAG Engine:** Supports various AI Agents by retrieving relevant answers from the corpus of support manuals
    - **Document AI Layout Parser:** Extracts structured content such as tables from manuals to build a RAG corpus

2. **Cloud Infrastructure on GCP**
    - **Cloud SQL:** Stores structured data about appliances, customers, registered appliances, and engineer records
    - **Cloud Storage:** Stores graphics, invoices, warranty docs, manuals and attachments linked to service requests
    - **Firestore:** Manages realtime data for service requests, and stores appliance specifications in a NoSQL format
    - **Cloud Run:** Hosts the backend services responsible for automatically assigning engineers to service requests
    - **Google Auth Platform:** Provides secure user authentication and session management, using Google Oauth2
    - **Google Maps SDK:** Address auto-complete, validation, geocoding, and distance-based engineer assignment

1. **Frontend and Communication Services**
    - **Streamlit:** Python-based frontend with support for custom components, & CSS to enhance the user interface
    - **Brevo:** Sends automated transactional and notification emails—such as service confirmations, and reminders
    - **Twilio:** For delivering realtime SMS alert to users about service status updates, and engineer visit notification

## Demo

Insert gif or link to demo

## Data Sources
The appliance dataset used in this project is entirely synthetic and was generated for demonstration purposes. Brand names, descriptions, and other technical specifications were fabricated using **Gemini 2.5** to simulate realistic product metadata across various categories such as refrigerators, washers & dryers, gas ranges and microwave ovens. Such an approach allowed for consistent, & scalable data creation without relying on any proprietary or sensitive information.

To visually represent these products within the application, corresponding images were generated using **Imagen 4 on Vertex AI Studio**. These images were generated to closely match the appliance specifications created in the metadata.

For implementing **Retrieval-Augmented Generation (RAG)** workflow, publicly available service manuals were sourced and preprocessed. A service manual was linked to each sub-category to demonstrate grounded response generation. These documents were parsed using the Google Cloud Document AI Layout Parser, and the content was indexed in a **RagManaged Vector Store** to enable the RAG engine to generate contextual responses for appliance troubleshooting

## Finding and Learnings

1. **Agentic AI enables task decomposition:** Breaking down responsibilities across multiple agents improved clarity, maintainability, and reusability of logic across user tasks, while allowing agents to focus on a single task at hand.
2. **Context management is key in multi-turn interactions:** Maintaining session state & context across different user intents was essential to avoid redundant questions & to ensure fluid conversations between the user & the agent
3. **RAG enhances response accuracy:** Integrating the RAG Engine pipeline grounded in service manuals significantly improved the relevance, factual grounding, and trustworthiness of the responses from the troubleshooting agent
4. **Tool/function calling is essential for dynamic interactions:** Using Gemini 2.5 Pro’s ability to invoke tools enabled real-time execution of tasks like fetching appliance data, updating customer profile, and logging service requests

## Screenshots

#### 1. Appliance Registration Agent Flow

![](https://github.com/thisisashwinraj/LogIQ-Smart-Appliance-Management/blob/main/assets/screenshots/chat/appliance_registration/chat_register_appliance_1.PNG)

![](https://github.com/thisisashwinraj/LogIQ-Smart-Appliance-Management/blob/main/assets/screenshots/chat/appliance_registration/chat_register_appliance_2.PNG)

![](https://github.com/thisisashwinraj/LogIQ-Smart-Appliance-Management/blob/main/assets/screenshots/chat/appliance_registration/chat_register_appliance_3.PNG)

![](https://github.com/thisisashwinraj/LogIQ-Smart-Appliance-Management/blob/main/assets/screenshots/chat/appliance_registration/chat_register_appliance_4.PNG)

![](https://github.com/thisisashwinraj/LogIQ-Smart-Appliance-Management/blob/main/assets/screenshots/chat/appliance_registration/registered_appliance_on_dashboard.PNG)

<HR>

#### 2. Product Enquiry Agent Flow

![](https://github.com/thisisashwinraj/LogIQ-Smart-Appliance-Management/blob/main/assets/screenshots/chat/product_enquiry/chat_product_enquiry_1.PNG)

![](https://github.com/thisisashwinraj/LogIQ-Smart-Appliance-Management/blob/main/assets/screenshots/chat/product_enquiry/chat_product_enquiry_2.PNG)

![](https://github.com/thisisashwinraj/LogIQ-Smart-Appliance-Management/blob/main/assets/screenshots/chat/product_enquiry/chat_product_enquiry_3.PNG)

![](https://github.com/thisisashwinraj/LogIQ-Smart-Appliance-Management/blob/main/assets/screenshots/chat/product_enquiry/chat_product_enquiry_4.PNG)

![](https://github.com/thisisashwinraj/LogIQ-Smart-Appliance-Management/blob/main/assets/screenshots/chat/product_enquiry/chat_product_enquiry_5.PNG)

To view the example screenshots of all the agents, click [here](https://github.com/thisisashwinraj/LogIQ-Smart-Appliance-Management/tree/main/assets/screenshots/chat)

## Authors
- [Ashwin Raj (@thisisashwinraj)](https://www.github.com/thisisashwinraj)

## Support and Feedback
Contributions are always welcome from the community. If you have any queries or would like to share some feedback, please drop a line at thisisashwinraj@gmail.com. You can also connect with the author on [LinkedIn](https://www.linkedin.com/in/thisisashwinraj/).
