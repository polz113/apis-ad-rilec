<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;

use App\Http\Controllers\ApisHRMasterController;
use App\Http\Controllers\ApisOUController;
use App\Http\Controllers\ApisUserProfileController;
use App\Http\Controllers\LdapActionController;

/*
|--------------------------------------------------------------------------
| API Routes
|--------------------------------------------------------------------------
|
*/

Route::group(['middleware'=>'auth:api'], function(){
    /* Route::put('/replicate', 'ApisADController@update'); 
    Route::get('/replicate', 'ApisADController@list'); */
    Route::put('/hr/HRMaster/replicate', 'ApisHRMasterController@update');
    Route::get('/hr/HRMaster/replicate', 'ApisHRMasterController@index');
    /* Seznam uporabnikov v nekem trenutku */
    Route::get('/api/userprofile/', 'ApisUserDataController@index');
    Route::get('/api/userprofile/{date}', 'ApisUserDataController@index');
    /* Podatki o posamezniku v nekem trenutku */
    Route::get('/api/userprofile/{date}/{id}', 'ApisUserDataController@show');
    /* Seznam org. enot v nekem trenutku */
    Route::get('/api/ou/{date}', [ApisOUController::class, 'index']);
    Route::get('/api/ou/', [ApisOUController::class, 'index']);
    /* Podrobnosti org. enote v nekem trenutku */
    Route::get('/api/ou/{date}/{uid}', 'ApisOUController@show');
    /* Drevo org. enot v nekem trenutku */
    Route::get('/api/outree/{date}', 'ApisOUController@tree_index');
    Route::get('/api/outree/', 'ApisOUController@tree_index');
    /* Podrobnosti prenosa podatkov v AD */
    Route::get('/api/dataset/', 'ADDatasetController@index');
    Route::get('/api/dataset/{id}', 'ADDatasetController@show');
    /* Ustvarjanje dataset-ov */
    Route::put('/api/dataset/{timestamp}', 'ADDatasetController@create');
    Route::put('/api/dataset/', 'ADDatasetController@create');
    /* Kopiranje podatkov v AD */
    Route::put('/api/ldapapply/{id}', 'ADDatasetController@create');
    Route::get('/api/ldapapply/', 'ADDatasetController@index');
    Route::get('/api/ldapapply/{id}', 'ADDatasetController@show');
    /*
    Route::get('/user', function (Request $request) {
    return $request->user();
  }); */
});
