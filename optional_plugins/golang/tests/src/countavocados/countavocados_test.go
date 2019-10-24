package main

import "testing"
import "fmt"

func TestEmptyContainers(t *testing.T) {
   total := Count(10, 0)
   if total != 0 {
      t.Errorf("No Avocados supposed to be present, but got %d", total)
   }
}

func TestNoContainers(t *testing.T) {
   total := Count(10, 0)
   if total != 0 {
      t.Errorf("No Avocados supposed to be present, but got %d", total)
   }
}

func TestingButNotReally() {
   return
}

func ExampleContainers() {
   fmt.Printf("Have %d Avocados", Count(3, 3))
   // Output: Have 9 Avocados
}
