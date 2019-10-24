package main

import "testing"

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
