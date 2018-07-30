import logging
import os

from base import Crawler
from utils import download_file
from app.constants import US_STATE_MAP
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.select import By

log = logging.getLogger(__name__)


class KaiserCrawler(Crawler):
	LOGIN_PAGE_URL = ''
	NEW_QUOTE_URL = ''

	def __init__(self, **kwargs):
		"""
		:param state: 2 digit state abbreviation
		:param effectiveDate: instance of datetime, effective date for the quote

		:param (optional) headless: should the driver run headless (invisible)?
		:param (optional) download_directory: local directory to save quotes
		:param (optional) chromedriver: local file path to the chromedriver
		"""
		self._state = kwargs.pop('state')
		self._effectiveDate = kwargs.pop('effectiveDate')

		self.counties = kwargs.pop('counties')
		self.countyErrors = {}

		super(KaiserCrawler, self).__init__(**kwargs)

	# Start of Abstract Properties
	@property
	def carrier(self):
		return {
			'CA': 'Kaiser CA',
			'GA': 'Kaiser GA',
			'DC': 'Kaiser Mid-Atlantic DC',
			'MD': 'Kaiser Mid-Atlantic MD',
			'VA': 'Kaiser Mid-Atlantic VA',
		}[self.state]

	@property
	def fullCarrier(self):
		if self.state == 'CA':
			return self.carrier
		return self.carrier + ' ' + self.state

	@property
	def state(self):
		return self._state

	@property
	def effectiveDate(self):
		return self._effectiveDate
	# End of Abstract Properties

	@property
	def fullState(self):
		return US_STATE_MAP[self.state].title()

	def handleEffectiveDate(self):
		# cast effective date into a string
		shortDate = str(self._effectiveDate)
		# grab the dropdown for effective dates using the Select class of selenium
		selectDate = Select(self.get_element_by_id('effective_date'))
		# selects the effective date option that matches a string version of the effective date, sans time
		selectDate.select_by_value(shortDate[0:10])

	def processQuote(self, county):
		if os.path.isfile('%s/%s' % (self.download_directory, '%s %s.xlsx' % (self.carrier, str(county)))):
			return

		self.get(KaiserCrawler.NEW_QUOTE_URL)

		# Finds name input, inputs name based off of county being quoted
		self.send_keys(self.get_element_by_name('name', clickable=True), str(county))
		#executeds the handleeffectiveDate function
		if self.state == 'MD' or self.state == 'DC' or self.state == 'VA':
			self.send_keys(self.get_element_by_id('zip_code', clickable=True), county.zip_code)
			self.wait(2)
			self.click(self.get_element_by_id('next_button', clickable=True))
			self.wait(2)
			if self.driver.find_elements_by_xpath('//*[@id="zip_code-error"]'):
				print('ZIP Code unavailable')
				return
			self.handleEffectiveDate()
			self.click(self.get_element_by_id('is_small_group_yes', clickable=True))
			self.click(self.get_element_by_id('hoursPerWeekY', clickable=True))
			self.click(self.get_element_by_id('kaiser_only_provider_y', clickable=True))
			self.click(self.get_element_by_id('are_defined_exclusions_n', clickable=True))
			self.click(self.get_element_by_id('currently_insured_as_kaiser_small_group_n', clickable=True))
			self.wait(2)
			self.click(self.get_element_by_id('next_button', clickable=True))
			self.wait(2)
		else:
			self.handleEffectiveDate()
			#pass zip code key into text input field for zip code
			self.send_keys(self.get_element_by_id('zip_code', clickable=True), county.zip_code)
			self.wait(2)
			# clicks the Continue button to move further along
			self.click(self.get_element_by_id('next_button', clickable=True))
			# waits 2 seconds before proceeding
			self.wait(2)

		if self.driver.find_elements_by_xpath('//*[@id="zip_code-error"]'):
			print('ZIP Code unavailable')
			return

		if self.state == 'CA':
			# creates rows for entering census
			number_of_rows = self.get_element_by_id('num_rows')
			number_of_rows.clear()
			self.send_keys(number_of_rows, 47)
			self.click(self.get_element_by_id('add_new_rows', clickable=True))
			# fills out census with employee details, starting with name
			for i in range(1, 49):
				self.send_keys(self.get_element_by_xpath('//*[@id="census_list"]/tbody['+str(i)+']/tr/td[1]/input'),"employee"+str(i))
			# inserts dates of birth-- for CA, inserts all possible age ranges due to Kaiser CA specifics
			date_of_births = self.driver.find_elements_by_class_name('dateDobMinAge')
			# pop is used here to pop off the last item in this list, which is a template that is hidden in the Kaiser portal
			date_of_births.pop()
			year = 2000
			for date_of_birth in date_of_births:
				self.send_keys(date_of_birth,"01/01/"+str(year))
				year -= 1
			zips = self.driver.find_elements_by_class_name('zipcodeUS')
			zips.pop()
			for zip in zips:
				self.send_keys(zip, county.zip_code)

			self.wait(2)

			# # advances to next stage
			second_to_last_employee = self.get_element_by_xpath('//*[@id="census_list"]/tbody[47]/tr/td[7]/span/input')
			second_to_last_employee.clear()
			self.send_keys(second_to_last_employee, 4)
			# click add dependents link
			self.click(self.get_element_by_xpath('//*[@id="census_list"]/tbody[47]/tr/td[7]/span/a'))
			# delete first dependent
			self.click(self.get_element_by_xpath('//*[@id="census_list"]/tbody[47]/tr[2]/td[7]/a'))
			# add names to children
			for i in range (2,5):
				self.send_keys(self.get_element_by_xpath('//*[@id="census_list"]/tbody[47]/tr['+str(i)+']/td[1]/input'), "child"+str(i))

			last_employee = self.get_element_by_xpath('//*[@id="census_list"]/tbody[48]/tr/td[7]/span/input')
			last_employee.clear()
			self.send_keys(last_employee, 2)
			# click add dependents link
			self.click(self.get_element_by_xpath('//*[@id="census_list"]/tbody[48]/tr/td[7]/span/a'))
			# delete first dependent
			self.click(self.get_element_by_xpath('//*[@id="census_list"]/tbody[48]/tr[2]/td[7]/a'))
			# add names to children
			self.send_keys(self.get_element_by_xpath('//*[@id="census_list"]/tbody[48]/tr[2]/td[1]/input'), "child2")
			# add dates of birth to all dependent children
			dep_date_of_births = self.driver.find_elements_by_class_name('dobDateChildMinAge')
			dep_year = 2001
			for dep_date_of_birth in dep_date_of_births:
				self.send_keys(dep_date_of_birth,"01/01/"+str(dep_year))
				dep_year += 1
			# advances to next stage
			self.click(self.get_element_by_id('next_button', clickable=True))

			#waits 2 seconds for page to load
			self.wait(2)

			# clicks download quote
			log.info('Downloading quote')
			self.click(self.get_element_by_xpath('//*[@id="rate_form"]/div[4]/div[1]/a[1]'))
			log.info('Quote downloaded')
			self.click(self.get_element_by_xpath('/html/body/div[6]/div/div[2]/div/div/p[3]/a[2]'))


		elif self.state == 'GA':
			# creates 1 row for second employee on census
			self.click(self.get_element_by_id('add_new_rows', clickable=True))
			# fills out census with employee details, starting with name
			for i in range(1, 3):
				self.send_keys(self.get_element_by_xpath('//*[@id="census_list"]/tbody['+str(i)+']/tr/td[1]/input'),"employee"+str(i))
			# inserts dates of birth-- for CA, inserts all possible age ranges due to Kaiser CA specifics
			date_of_births = self.driver.find_elements_by_class_name('dateDobMinAge')
			# pop is used here to pop off the last item in this list, which is a template that is hidden in the Kaiser portal
			date_of_births.pop()
			for date_of_birth in date_of_births:
				self.send_keys(date_of_birth,"01/01/1980")
			zips = self.driver.find_elements_by_class_name('zipcodeUS')
			zips.pop()
			for zip in zips:
				self.send_keys(zip, county.zip_code)

			self.wait(2)
			# advances to next stage
			self.click(self.get_element_by_id('next_button', clickable=True))

			#waits 2 seconds for page to load
			self.wait(2)

			# clicks download quote
			log.info('Downloading quote')
			self.click(self.get_element_by_xpath('//*[@id="rate_form"]/div[4]/div[1]/a[1]'))
			log.info('Quote downloaded')
			self.click(self.get_element_by_xpath('/html/body/div[6]/div/div[2]/div/div/p[3]/a[1]'))


		elif self.state == 'MD' or self.state == 'DC' or self.state == 'VA':
			self.click(self.get_element_by_xpath('//*[@id="census_form"]/p[2]/label[2]/input', clickable=True))
			# creates 1 row for second employee on census
			self.click(self.get_element_by_id('add_new_rows', clickable=True))
			# fills out census with employee details
			for i in range(1, 3):
				self.send_keys(self.get_element_by_xpath('//*[@id="census_list"]/tbody['+str(i)+']/tr/td[2]/input'),"employee"+str(i))
				self.click(self.get_element_by_xpath('//*[@id="census_list"]/tbody['+str(i)+']/tr/td[6]/select/option[1]', clickable=True))
			# inserts dates of birth-- for CA, inserts all possible age ranges due to Kaiser CA specifics
			date_of_births = self.driver.find_elements_by_class_name('dateDobMinAge')
			# pop is used here to pop off the last item in this list, which is a template that is hidden in the Kaiser portal
			date_of_births.pop()
			for date_of_birth in date_of_births:
				self.send_keys(date_of_birth,"01/01/1980")
			# advances to next stage
			self.click(self.get_element_by_id('next_button', clickable=True))
			#waits 2 seconds for page to load
			self.wait(2)
			# clicks download quote
			log.info('Downloading quote')
			self.click(self.get_element_by_xpath('//*[@id="rate_form"]/div[4]/div[1]/a[1]'))
			log.info('Quote downloaded')
			self.click(self.get_element_by_xpath('/html/body/div[6]/div/div[2]/div/div/p[3]/a[2]'))
			#close download quote window
			self.click(self.get_element_by_xpath('/html/body/div[6]/div/div[2]/div/div/p[3]/a[3]'))
			#return to census for editing
			self.wait(2)
			self.click(self.get_element_by_xpath('/html/body/div[4]/div/div[3]/ul/li[3]/a'))
			self.wait(2)
			self.click(self.get_element_by_xpath('//*[@id="census_form"]/p[2]/label[3]/input', clickable=True))
			# advances to next stage
			self.click(self.get_element_by_id('next_button', clickable=True))
			#waits 2 seconds for page to load
			self.wait(2)
			# clicks download quote
			log.info('Downloading quote')
			self.click(self.get_element_by_xpath('//*[@id="rate_form"]/div[4]/div[1]/a[1]'))
			log.info('Quote downloaded')
			self.click(self.get_element_by_xpath('/html/body/div[6]/div/div[2]/div/div/p[3]/a[2]'))


	def crawl(self):
		log.info('Logging in')
		if self.state == 'CA':
			KaiserCrawler.LOGIN_PAGE_URL = 'https://ca.kpquote.com/index.php/'
			KaiserCrawler.NEW_QUOTE_URL = 'https://ca.kpquote.com/quote/step1'
		elif self.state == 'GA':
			KaiserCrawler.LOGIN_PAGE_URL = 'https://ga.kpquote.com/index.php/'
			KaiserCrawler.NEW_QUOTE_URL = 'https://ga.kpquote.com/quote/step1'
		elif self.state == 'MD' or 'DC' or 'VA':
			KaiserCrawler.LOGIN_PAGE_URL = 'https://mas.kpquote.com/'
			KaiserCrawler.NEW_QUOTE_URL = 'https://mas.kpquote.com/quote/step1'

		username = raw_input('Username: ')
		password = raw_input('Password: ')

		self.get(KaiserCrawler.LOGIN_PAGE_URL)
		self.send_keys(self.get_element_by_name('username', clickable=True), username)
		self.send_keys(self.get_element_by_name('password', clickable=True), password)
		self.click(self.get_element_by_class_name('form_button_green', clickable=True))

		log.info('Logged in')

		for cIdx, county in enumerate(self.counties):
			log.info('Quoting for %s' % county)

			self.processQuote(county)

			log.info('Finished quoting')

		log.info('Logging out')

		self.execute_script("location.href='/ehb/c/portal/logout?redirectTo=logoutSuccess';")

		log.info('Logged out')
