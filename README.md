# Venue Catalog

A Flask/SQLalchemy application that uses Google Geocode and Foursquare APIs
to search for venues around any given location. CRUD operations
allow users with correct permissions to save search results to the database,
modify or delete existing content, or add their own custom content.

It is recommended to use the virtual machine configuration provided below.
Download Vagrant from [vagrantup.com](https://www.vagrantup.com/downloads.html),
then follow these steps after installation:

* Download the virtual machine configuration [here](https://d17h27t6h515a5.cloudfront.net/topher/2017/August/59822701_fsnd-virtual-machine/fsnd-virtual-machine.zip)

* Clone the project into ```FSND-Virtual-Machine/vagrant```

* Navigate to the above directory on the command line and run ```vagrant up```
to connect to the virtual machine, then log in with ```vagrant ssh```

* Move to the project directory with ```cd /vagrant/venue-catalog-master```

* Run ```python3 app.py``` and access the web application at http://localhost:8000

For inquiries, post an issue on the [github repository page](https://github.com/eicksl/Venue-Catalog/issues).
