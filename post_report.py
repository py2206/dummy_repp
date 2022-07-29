import requests
import json
from tools.reportportal.src.report_portal_const import *

class HttpRequest(object):
 
    def __init__(self) -> None: 
        self.headers = {
            "Content-Type":"application/json",
            "Authorization":"bearer " + self.rp_uuid 
        }
    def send_http_request(self, method:str, **args) -> dict:
        """
        This method sends http request.
        Return: response 
        """
        try:
            args["headers"] = self.headers
            args["verify"] = False
            resp = getattr(requests, "request")(method, **args)
            return resp
        except Exception as error:
            raise Exception(error)

class ReportPortal(HttpRequest):
   
    def __init__(self, portal_project, dashboard, rp_uuid, repo_name, rp_endpoint) -> None:
        self.rp_project_name = portal_project 
        self.rp_uuid = rp_uuid
        self.base_url = str(rp_endpoint) +  RP_END_POINT
        self.rp_dashboard_name = " ".join([word for word in dashboard.split('_')]).upper()
        self.filter_name = repo_name
        HttpRequest.__init__(self)
    
    def check_dashboard_exist(self) -> bool:
        """
        This method checks for existing dashboard in reportportal
        """
        request_data = dict()
        current_page_number = 1
        totalPages = 1
        dashboard_exist = False
        while current_page_number <= totalPages : 
            request_data["url"] = self.base_url + self.rp_project_name +  '/' + DASHBOARD_END_POINT + PAGE_NUMBER_FILETR + str(current_page_number) + PAGE_SIZE_FILETR
            response_ = self.send_http_request(GET, **request_data) 
            if response_.status_code == OKAY_RESPONSE_CODE:
                dashboard_response = json.loads(response_.content)
                totalPages = dashboard_response.get("page").get("totalPages")
                current_page_number = dashboard_response.get("page").get("number") + 1
                if not any(dasboard['name'] == self.rp_dashboard_name for dasboard in dashboard_response["content"]): 
                    continue
                else:
                    # means dashboard exist
                    print(f"{self.rp_dashboard_name} exist !!!") 
                    dashboard_exist = True
                    
            else:
                raise Exception(response_.content)
        return dashboard_exist 

    def check_service_launch_execution(self):
        """
        This method checks launch execution for component or service.
        """
        request_data = dict()
        request_data["url"] = self.base_url + self.rp_project_name +  '/' + LAUNCH_END_POINT + PAGE_SIZE + SORTING_END_POINT
        response_ = self.send_http_request(GET, **request_data) 
        if response_.status_code == OKAY_RESPONSE_CODE:
            launch_response = json.loads(response_.content)
            if not any(launch['name'] == self.launch_name for launch in launch_response["content"]): 
                return False
            else:
                return True
        else:
            raise Exception(response_.content)

    def create_filter_for_service(self) -> None:
        """
        This method creates filter for given component or service 
        """
        #  launch name and filter name should be  same 
        self.launch_name = self.filter_name
        if self.check_service_launch_execution() == False:
            print(f"{self.launch_name} does not exist in launch execution in RP !!! ")
            return False
        request_data = dict()
        request_data["url"] = self.base_url + self.rp_project_name +  '/' + FILTER_END_POINT
        try:
            FILTER_PAYLOAD["conditions"][0]["value"] = self.launch_name
            FILTER_PAYLOAD["name"] = self.launch_name
            request_data["data"] = json.dumps(FILTER_PAYLOAD)
            response_    = self.send_http_request(POST, **request_data) 
            if response_.status_code == CREATED_RESPONSE_CODE:
                self.filter_id = json.loads(response_.content)["id"]
                print(f"{self.launch_name} filter created successfully !!!")
            else:
                error = f"{self.launch_name} filter creation failed with reason {response_.content}"
                raise Exception(error, response_)
        except Exception as error:
            raise Exception(error)
        
    def create_dashboard(self) -> None:
        """
        This method creates dashboard for given service.
        """
        if self.create_filter_for_service() == False:
            return False
        request_data = dict()
        request_data["url"] = self.base_url + self.rp_project_name +  '/' + DASHBOARD_END_POINT
        try:
            DASHBOARD_PAYLOAD["name"] = self.rp_dashboard_name
            DASHBOARD_PAYLOAD["description"] = f"Dashboard of  {self.launch_name}  component "
            request_data["data"] = json.dumps(DASHBOARD_PAYLOAD)
            response_    = self.send_http_request(POST, **request_data) 
            if response_.status_code == CREATED_RESPONSE_CODE:
                self.dashboard_id = json.loads(response_.content)["id"] 
                print(f"{self.rp_dashboard_name} dashboard created successfully !!!")
            else:
                error = f"{self.rp_dashboard_name} dashboard creation failed with reason {response_.content}"
                raise Exception(error, response_)
        except Exception as error:
            raise Exception(error) 

    def add_widget_to_dashboard(self, widgetType, index) -> None:
        """
        This method add widget for dashboard.
        """
        request_data = dict()
        request_data["url"] = self.base_url + self.rp_project_name +  '/' + DASHBOARD_END_POINT + '/' + str(self.dashboard_id) + '/' + WIDGET_ADD_END_POINT
        ADD_WIDGET_PAYLOAD["addWidget"]["widgetId"] = self.widget_id
        ADD_WIDGET_PAYLOAD["addWidget"]["widgetName"] = self.widget_name
        ADD_WIDGET_PAYLOAD["addWidget"]["widgetType"] = widgetType
        if index % 2 != 0:
            ADD_WIDGET_PAYLOAD["addWidget"]["widgetPosition"]["positionX"] = 0
            ADD_WIDGET_PAYLOAD["addWidget"]["widgetPosition"]["positionY"] = 7 * index  
        else:
            ADD_WIDGET_PAYLOAD["addWidget"]["widgetPosition"]["positionX"] = 6
            ADD_WIDGET_PAYLOAD["addWidget"]["widgetPosition"]["positionY"] = 0
        request_data["data"] = json.dumps(ADD_WIDGET_PAYLOAD)
        try:
            response_    = self.send_http_request(PUT, **request_data)  
            if response_.status_code == OKAY_RESPONSE_CODE:
                print(f"{self.widget_name} added successfully to dashboad {self.rp_dashboard_name}") 
            else:
                raise Exception (f"{self.widget_name} failed with reason {response_.content}")
        except Exception as err:
            raise Exception(err)


    def create_overall_statistic_widget(self, url, widgetType, index)-> None:
        """
        This method creates overall statistic widget for service
        """
        request_data = dict()
        request_data["url"] = url
        self.widget_name = self.rp_dashboard_name + "_" + str(index)
        OVERALL_STATISTIC_CHART_PAYLOAD["name"] = self.widget_name
        OVERALL_STATISTIC_CHART_PAYLOAD["filterIds"] = [self.filter_id]
        OVERALL_STATISTIC_CHART_PAYLOAD["filters"][0]["value"] = self.filter_id
        OVERALL_STATISTIC_CHART_PAYLOAD["filters"][0]["name"] = self.launch_name
        request_data["data"] = json.dumps(OVERALL_STATISTIC_CHART_PAYLOAD)
        response_    = self.send_http_request(POST, **request_data)  
        if response_.status_code == CREATED_RESPONSE_CODE:
                self.widget_id = json.loads(response_.content)["id"] 
                print(f"{NON_PASSED_TEST_CASE_TREND_CHART_PAYLOAD['name']} widget created successfully !!!")
                return self.add_widget_to_dashboard(widgetType, index)
        else:
            error = f"{self.widget_name} widget creation failed with reason {response_.content}"
            raise Exception(error, response_) 
    
    def create_passing_summary_launch_widget(self, url,widgetType,index)-> None:
        """
        This method creates summary launch widget for service
        """
        request_data = dict()
        request_data["url"] = url
        self.widget_name = self.rp_dashboard_name + "_" + str(index)
        PASSING_RATE_SUMMARY_CHART_PAYLOAD["name"] = self.widget_name
        PASSING_RATE_SUMMARY_CHART_PAYLOAD["filterIds"] = [self.filter_id]
        PASSING_RATE_SUMMARY_CHART_PAYLOAD["filters"][0]["value"] = self.filter_id
        PASSING_RATE_SUMMARY_CHART_PAYLOAD["filters"][0]["name"] = self.launch_name
        request_data["data"] = json.dumps(PASSING_RATE_SUMMARY_CHART_PAYLOAD)
        response_    = self.send_http_request(POST, **request_data)  
        if response_.status_code == CREATED_RESPONSE_CODE:
                self.widget_id = json.loads(response_.content)["id"] 
                print(f"{self.widget_name} widget created successfully !!!")
                return self.add_widget_to_dashboard(widgetType, index)
        else:
            error = f"{self.widget_name} widget creation failed with reason {response_.content}"
            raise Exception(error, response_) 

    def create_passing_rate_per_launch_widget(self, url,widgetType, index)->None:
        """
        This method creates passing per rate launch widget for service
        """
        request_data = dict()
        request_data["url"] = url
        self.widget_name = self.rp_dashboard_name + "_" + str(index)
        PASSING_PER_RATE_LAUNCH_CHART_PAYLOAD["name"] = self.widget_name
        PASSING_PER_RATE_LAUNCH_CHART_PAYLOAD["filterIds"] = [self.filter_id]
        PASSING_PER_RATE_LAUNCH_CHART_PAYLOAD["contentParameters"]["widgetOptions"]["launchNameFilter"] = self.launch_name
        request_data["data"] = json.dumps(PASSING_PER_RATE_LAUNCH_CHART_PAYLOAD)
        response_    = self.send_http_request(POST, **request_data)  
        if response_.status_code == CREATED_RESPONSE_CODE:
                self.widget_id = json.loads(response_.content)["id"] 
                print(f"{self.widget_name} widget created successfully !!!")
                return self.add_widget_to_dashboard(widgetType, index)
        else:
            error = f"{self.widget_name} widget creation failed with reason {response_.content}"
            raise Exception(error, response_) 

    
    def create_launch_static_and_issue_widget(self, url,widgetType, index)->None:
        """
        This method creates launch and issue widget for service 
        """
        request_data = dict()
        request_data["url"] = url
        self.widget_name = self.rp_dashboard_name + "_" + str(index)
        LAUNCH_EXECUTION_AND_STATISTIC_CHART_PAYLOAD["name"] = self.widget_name
        LAUNCH_EXECUTION_AND_STATISTIC_CHART_PAYLOAD["filterIds"] = [self.filter_id]
        LAUNCH_EXECUTION_AND_STATISTIC_CHART_PAYLOAD["filters"][0]["value"] = self.filter_id
        LAUNCH_EXECUTION_AND_STATISTIC_CHART_PAYLOAD["filters"][0]["name"] = self.launch_name
        request_data["data"] = json.dumps(LAUNCH_EXECUTION_AND_STATISTIC_CHART_PAYLOAD)
        response_    = self.send_http_request(POST, **request_data)  
        if response_.status_code == CREATED_RESPONSE_CODE:
                self.widget_id = json.loads(response_.content)["id"] 
                print(f"{self.widget_name} widget created successfully !!!")
                return self.add_widget_to_dashboard(widgetType, index)
        else:
            error = f"{self.widget_name} widget creation failed with reason {response_.content}"
            raise Exception(error, response_) 

    def create_most_failed_test_case_widget(self, url,widgetType, index)->None:
        """
        This method creates most failed testcase widget for service 
        """
        request_data = dict()
        request_data["url"] = url
        self.widget_name = self.rp_dashboard_name + "_" + str(index)
        MOST_FAILED_TEST_CASE_CHART_PAYLOAD["name"] = self.widget_name
        MOST_FAILED_TEST_CASE_CHART_PAYLOAD["filterIds"] = [self.filter_id]
        MOST_FAILED_TEST_CASE_CHART_PAYLOAD["contentParameters"]["widgetOptions"]["launchNameFilter"] = self.launch_name
        request_data["data"] = json.dumps(MOST_FAILED_TEST_CASE_CHART_PAYLOAD)
        response_    = self.send_http_request(POST, **request_data)  
        if response_.status_code == CREATED_RESPONSE_CODE:
                self.widget_id = json.loads(response_.content)["id"] 
                print(f"{self.widget_name} widget created successfully !!!")
                return self.add_widget_to_dashboard(widgetType, index)
        else:
            error = f"{self.widget_name} widget creation failed with reason {response_.content}"
            raise Exception(error, response_) 
    def create_failed_test_case_widget(self, url,widgetType, index)->None:
        """
        This method creates failed test case widget for service 
        """
        request_data = dict()
        request_data["url"] = url
        self.widget_name = self.rp_dashboard_name + "_" + str(index)
        FAILED_TEST_CASE_TREND_CHART_PAYLOAD["name"] = self.widget_name
        FAILED_TEST_CASE_TREND_CHART_PAYLOAD["filterIds"] = [self.filter_id]
        FAILED_TEST_CASE_TREND_CHART_PAYLOAD["contentParameters"]["widgetOptions"]["launchNameFilter"] = self.launch_name
        request_data["data"] = json.dumps(FAILED_TEST_CASE_TREND_CHART_PAYLOAD)
        response_    = self.send_http_request(POST, **request_data)  
        if response_.status_code == CREATED_RESPONSE_CODE:
                self.widget_id = json.loads(response_.content)["id"] 
                print(f"{self.widget_name} widget created successfully !!!")
                return self.add_widget_to_dashboard(widgetType, index)
        else:
            error = f"{self.widget_name} widget creation failed with reason {response_.content}"
            raise Exception(error, response_) 

    def create_flaky_test_case_widget(self, url,widgetType, index)->None:
        """
        This method creates flaky test case widget for service
        """
        request_data = dict()
        request_data["url"] = url
        self.widget_name = self.rp_dashboard_name + "_" + str(index)
        FLAKY_TEST_CASE_CHART_PAYLOAD["name"] = self.widget_name
        FLAKY_TEST_CASE_CHART_PAYLOAD["filterIds"] = [self.filter_id]
        FLAKY_TEST_CASE_CHART_PAYLOAD["contentParameters"]["widgetOptions"]["launchNameFilter"] = self.launch_name
        request_data["data"] = json.dumps(FLAKY_TEST_CASE_CHART_PAYLOAD)
        response_    = self.send_http_request(POST, **request_data)  
        if response_.status_code == CREATED_RESPONSE_CODE:
                self.widget_id = json.loads(response_.content)["id"] 
                print(f"{self.widget_name} widget created successfully !!!")
                return self.add_widget_to_dashboard(widgetType, index)
        else:
            error = f"{self.widget_name} widget creation failed with reason {response_.content}"
            raise Exception(error, response_) 

    def create_most_time_consuming_wiget(self, url,widgetType, index)->None:
        """
        This method creates most time consuming widget for service.
        """
        request_data = dict()
        request_data["url"] = url
        self.widget_name = self.rp_dashboard_name + "_" + str(index)
        MOST_TIME_CONSUMING_PAYLOAD["name"] = self.widget_name
        MOST_TIME_CONSUMING_PAYLOAD["filterIds"] = [self.filter_id]
        MOST_TIME_CONSUMING_PAYLOAD["contentParameters"]["widgetOptions"]["launchNameFilter"] = self.launch_name
        request_data["data"] = json.dumps(MOST_TIME_CONSUMING_PAYLOAD)
        response_    = self.send_http_request(POST, **request_data)  
        if response_.status_code == CREATED_RESPONSE_CODE:
                self.widget_id = json.loads(response_.content)["id"] 
                print(f"{self.widget_name} widget created successfully !!!")
                return self.add_widget_to_dashboard(widgetType, index)
        else:
            error = f"{self.widget_name} widget creation failed with reason {response_.content}"
            raise Exception(error, response_) 

    def create_launch_static_widget(self, url,widgetType, index)->None:
        """
        This method creates launch static widget for service.
        """
        request_data = dict()
        request_data["url"] = url
        self.widget_name = self.rp_dashboard_name + "_" + "9"
        LAUNCH_STATIC_CHART_PAYLOAD["name"] = self.widget_name
        LAUNCH_STATIC_CHART_PAYLOAD["filterIds"] = [self.filter_id]
        LAUNCH_STATIC_CHART_PAYLOAD["filters"][0]["value"] = self.filter_id
        LAUNCH_STATIC_CHART_PAYLOAD["filters"][0]["name"] = self.launch_name
        request_data["data"] = json.dumps(LAUNCH_STATIC_CHART_PAYLOAD)
        response_    = self.send_http_request(POST, **request_data)  
        if response_.status_code == CREATED_RESPONSE_CODE:
                self.widget_id = json.loads(response_.content)["id"] 
                print(f"{LAUNCH_STATIC_CHART_PAYLOAD['name']} widget created successfully !!!")
                return self.add_widget_to_dashboard(widgetType, index)
        else:
            error = f"{self.widget_name} widget creation failed with reason {response_.content}"
            raise Exception(error, response_) 

    def create_non_passed_test_case_widget(self, url, widgetType, index)->None:
        """
        This method creates non passed test case widget for service.
        """
        request_data = dict()
        request_data["url"] = url
        self.widget_name = self.rp_dashboard_name + "_" + str(index)
        NON_PASSED_TEST_CASE_TREND_CHART_PAYLOAD["name"] = self.widget_name
        NON_PASSED_TEST_CASE_TREND_CHART_PAYLOAD["filterIds"] = [self.filter_id]
        NON_PASSED_TEST_CASE_TREND_CHART_PAYLOAD["filters"][0]["value"] = self.filter_id
        NON_PASSED_TEST_CASE_TREND_CHART_PAYLOAD["filters"][0]["name"] = self.launch_name
        request_data["data"] = json.dumps(NON_PASSED_TEST_CASE_TREND_CHART_PAYLOAD)
        response_    = self.send_http_request(POST, **request_data)  
        if response_.status_code == CREATED_RESPONSE_CODE:
                self.widget_id = json.loads(response_.content)["id"] 
                print(f"{NON_PASSED_TEST_CASE_TREND_CHART_PAYLOAD['name']} widget created successfully !!!")
                return self.add_widget_to_dashboard(widgetType, index)
        else:
            error = f"{self.widget_name} widget creation failed with reason {response_.content}"
            raise Exception(error, response_) 
        
        
    def create_widget(self, methodTorun)->None:
        """
        This method invokes create wiget for service.
        """
        if methodTorun() == False:
            print("Error in creating filter or dashboard !!!")
            return 
        url = self.base_url + self.rp_project_name +  '/' + WIDGET_END_POINT
        widgets = {
            NOT_PASSED: self.create_non_passed_test_case_widget,
            LAUNCH_STATIC:self.create_launch_static_widget,
            MOST_TIME_CONSUMING:self.create_most_time_consuming_wiget,
            FLAKY_TEST_CASE:self.create_flaky_test_case_widget,
            FAILED_TEST_CASE_TREND:self.create_failed_test_case_widget,
            MOST_FAILED_TEST_CASE:self.create_most_failed_test_case_widget,
            LAUNCH_EXECUTION:self.create_launch_static_and_issue_widget,
            PASSING_RATE_PER_LAUNCH:self.create_passing_rate_per_launch_widget,
            PASSING_RATE_SUMMARY:self.create_passing_summary_launch_widget,
            OVERALL_STATISTIC_CHART:self.create_overall_statistic_widget

        }
        for index, widget in enumerate(reversed(widgets), start=1):
            widgets[widget](url,widget, index)
