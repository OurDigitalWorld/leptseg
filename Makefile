leptseg.so: leptseg.o
	gcc -llept -shared -o leptseg.so leptseg.o

leptseg.o: leptseg.c
	gcc -c -Wall -Werror -fpic  -I/usr/include/leptonica leptseg.c 

clean:
	rm -f *.o *.so

